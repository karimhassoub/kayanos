import frappe
from frappe.utils import flt

def on_payment_voucher_update(doc, method):
    """
    Hooked on Payment Entry and Journal Entry:
    on_submit, on_cancel, on_update_after_submit
    Extracts all Sales Invoice references from both current and previous states,
    and resynchronizes their linked RE Billing Events.
    """
    if doc.doctype not in ("Payment Entry", "Journal Entry"):
        return

    invoices = set()

    # Helper to extract from a list of rows
    def extract_invoices(rows):
        if not rows:
            return
        for row in rows:
            ref_type = row.get("reference_doctype") or row.get("reference_type")
            ref_name = row.get("reference_name")
            if ref_type == "Sales Invoice" and ref_name:
                invoices.add(ref_name)

    # 1. Current references
    if doc.doctype == "Payment Entry":
        extract_invoices(doc.get("references"))
    else:
        extract_invoices(doc.get("accounts"))

    # 2. Previous references (from doc_before_save)
    doc_before = doc.get_doc_before_save()
    if doc_before:
        if doc_before.doctype == "Payment Entry":
            extract_invoices(doc_before.get("references"))
        else:
            extract_invoices(doc_before.get("accounts"))

    # Resynchronize all found invoices
    for inv in invoices:
        sync_collections_for_invoice(inv)

def sync_all_collections():
    """
    Scheduled hourly job to guarantee eventual consistency for 
    any manual DB bypasses or Payment Reconciliation skips.
    """
    # Find all Billing Events that are Invoiced but not fully settled/returned/failed
    # For safety, just sync all Invoiced events where collection_status not in ('Fully Settled', 'Fully Returned', 'Over-Settled (Credit)')
    # Or just sync all 'Invoiced' events to be completely safe against unreconciliation
    events = frappe.get_all(
        "RE Billing Event",
        filters={"status": "Invoiced", "erpnext_invoice_ref": ["is", "set"]},
        pluck="erpnext_invoice_ref"
    )
    # Deduplicate in case multiple events point to same invoice (rare but possible in error states)
    invoices = set(events)
    for inv in invoices:
        try:
            sync_collections_for_invoice(inv)
        except Exception as e:
            frappe.log_error(title=f"Failed to sync collections for {inv}", message=frappe.get_traceback())

def sync_collections_for_invoice(invoice_name: str):
    """
    Idempotent calculation of collections for a specific Sales Invoice.
    """
    # 1. Check if invoice is linked to an RE Billing Event
    events = frappe.get_all(
        "RE Billing Event",
        filters={"erpnext_invoice_ref": invoice_name},
        pluck="name"
    )
    if not events:
        return

    # Load the actual invoice
    if not frappe.db.exists("Sales Invoice", invoice_name):
        return
        
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    
    # Process each linked event (usually just 1)
    for event_name in events:
        _process_billing_event_sync(event_name, invoice)

def get_billing_event_projection(event_name: str, invoice):
    """
    Exposes the 5I-D calculation as a pure getter without mutating the DB.
    """
    event = frappe.get_doc("RE Billing Event", event_name)

    if not event.currency or not invoice.currency or event.currency != invoice.currency:
        frappe.throw(
            f"Currency mismatch or missing: Billing Event '{event.name}' ({event.currency}) "
            f"vs Sales Invoice '{invoice.name}' ({invoice.currency})"
        )

    precision = invoice.precision("outstanding_amount")

    raw_gross = invoice.grand_total
    raw_erpnext_outstanding = invoice.outstanding_amount
    raw_returned = event.returned_amount or 0.0
    raw_cash = 0.0
    raw_adj = 0.0

    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "docstatus": 1
        },
        fields=["allocated_amount"]
    )
    raw_cash += sum(flt(r.allocated_amount) for r in pe_refs)

    je_accounts = frappe.get_all(
        "Journal Entry Account",
        filters={
            "reference_type": "Sales Invoice",
            "reference_name": invoice.name,
            "docstatus": 1
        },
        fields=["credit_in_account_currency", "parent"]
    )
    
    if je_accounts:
        for r in je_accounts:
            raw_adj += flt(r.credit_in_account_currency)

    gross_invoiced_amount = flt(raw_gross, precision)
    returned_amount = flt(raw_returned, precision)
    cash_allocated = flt(raw_cash, precision)
    adjustment_allocated = flt(raw_adj, precision)
    erpnext_outstanding = flt(raw_erpnext_outstanding, precision)

    projected_balance = flt(gross_invoiced_amount - returned_amount - cash_allocated - adjustment_allocated, precision)

    if projected_balance < 0.0:
        collection_status = "Over-Settled (Credit)"
    elif projected_balance == 0.0:
        if cash_allocated == 0.0 and adjustment_allocated == 0.0:
            collection_status = "Fully Returned"
        else:
            collection_status = "Fully Settled"
    else: 
        if cash_allocated == 0.0 and adjustment_allocated == 0.0:
            collection_status = "Unpaid"
        else:
            collection_status = "Partially Settled"

    return {
        "gross_invoiced_amount": gross_invoiced_amount,
        "cash_allocated": cash_allocated,
        "adjustment_allocated": adjustment_allocated,
        "erpnext_outstanding": erpnext_outstanding,
        "projected_balance": projected_balance,
        "collection_status": collection_status
    }

def _process_billing_event_sync(event_name: str, invoice):
    # Lock for update
    frappe.db.get_value("RE Billing Event", event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", event_name)

    proj = get_billing_event_projection(event_name, invoice)

    event.db_set("gross_invoiced_amount", proj["gross_invoiced_amount"], update_modified=True)
    event.db_set("cash_allocated", proj["cash_allocated"], update_modified=True)
    event.db_set("adjustment_allocated", proj["adjustment_allocated"], update_modified=True)
    event.db_set("projected_balance", proj["projected_balance"], update_modified=True)
    event.db_set("erpnext_outstanding", proj["erpnext_outstanding"], update_modified=True)
    event.db_set("collection_status", proj["collection_status"], update_modified=True)

