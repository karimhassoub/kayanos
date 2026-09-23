import frappe
from frappe.utils import flt
import hashlib
from kayanos.kayanos_core.erpnext_collection_service import get_billing_event_projection

def get_finding_signature(finding_type, doc_type, doc_name):
    raw = f"{finding_type}-{doc_type}-{doc_name}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def log_finding(finding_type, severity, doc_type, doc_name, expected_value="", actual_value="", active_signatures=None):
    signature = get_finding_signature(finding_type, doc_type, doc_name)
    
    if active_signatures is not None:
        active_signatures.add(signature)

    existing = frappe.db.get_value("RE Integrity Finding", {"finding_signature": signature}, "name")
    
    if existing:
        doc = frappe.get_doc("RE Integrity Finding", existing)
        if doc.status == "Accepted/Expected":
            return # Leave it alone
        if doc.status == "Resolved":
            # Regression occurred
            doc.status = "Open"
            doc.expected_value = str(expected_value)
            doc.actual_value = str(actual_value)
            doc.save(ignore_permissions=True)
        else:
            # Update values if they changed
            if doc.expected_value != str(expected_value) or doc.actual_value != str(actual_value):
                doc.expected_value = str(expected_value)
                doc.actual_value = str(actual_value)
                doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("RE Integrity Finding")
        doc.finding_signature = signature
        doc.finding_type = finding_type
        doc.severity = severity
        doc.reference_document_type = doc_type
        doc.reference_document_name = doc_name
        doc.expected_value = str(expected_value)
        doc.actual_value = str(actual_value)
        doc.status = "Open"
        doc.insert(ignore_permissions=True)

def run_daily_integrity_audit(targeted_doc_name=None):
    active_signatures = set()

    # 1. Billing Event Invariants & 5I-D Integrity
    billing_events = frappe.get_all(
        "RE Billing Event",
        filters={"status": "Invoiced"},
        fields=["name", "erpnext_invoice_ref", "currency", "gross_invoiced_amount", 
                "cash_allocated", "adjustment_allocated", "erpnext_outstanding", 
                "projected_balance", "collection_status", "customer", "unit"],
        limit_page_length=5000
    )

    for be in billing_events:
        if targeted_doc_name and be.name != targeted_doc_name:
            continue

        if not be.erpnext_invoice_ref:
            continue

        if not frappe.db.exists("Sales Invoice", be.erpnext_invoice_ref):
            log_finding("Missing Invoice", "Critical", "RE Billing Event", be.name,
                        "Invoice Exists", "Missing", active_signatures)
            continue

        inv = frappe.get_doc("Sales Invoice", be.erpnext_invoice_ref)
        
        if inv.docstatus == 2:
            returns = frappe.db.exists("RE Billing Event Return", {"billing_event": be.name, "docstatus": 1})
            if not returns:
                log_finding("Unmanaged Cancellation", "Critical", "RE Billing Event", be.name,
                            "Has Valid Return", "No Return Found", active_signatures)
            continue

        if inv.currency != be.currency:
            log_finding("Currency Mismatch", "Critical", "RE Billing Event", be.name,
                        be.currency, inv.currency, active_signatures)

        # Gap 1: Customer Mismatch
        if inv.customer != be.customer:
            log_finding("Customer Mismatch", "Critical", "RE Billing Event", be.name,
                        be.customer, inv.customer, active_signatures)

        # Gap 2: Unit Mismatch
        if be.unit:
            unit_doc = frappe.get_cached_doc("RE Unit", be.unit)
            if unit_doc and unit_doc.shadow_item:
                item_codes = [row.item_code for row in inv.items]
                if unit_doc.shadow_item not in item_codes:
                    log_finding("Unit Mismatch", "Critical", "RE Billing Event", be.name,
                                unit_doc.shadow_item, ", ".join(item_codes), active_signatures)

        try:
            proj = get_billing_event_projection(be.name, inv)
            mismatches = []
            for field in ["gross_invoiced_amount", "cash_allocated", "adjustment_allocated", "erpnext_outstanding", "projected_balance"]:
                if flt(proj[field]) != flt(be.get(field)):
                    mismatches.append(f"{field}: expected {proj[field]} got {be.get(field)}")
            
            if proj["collection_status"] != be.collection_status:
                mismatches.append(f"status: expected {proj['collection_status']} got {be.collection_status}")

            if mismatches:
                log_finding("State Mismatch", "Warning", "RE Billing Event", be.name,
                            "Match 5I-D Projection", ", ".join(mismatches), active_signatures)
        except Exception as e:
            frappe.log_error("Reconciliation Projection Error", str(e))

    # 2. Orphan Payment Schedules
    schedules = frappe.db.sql("""
        SELECT sch.name, sch.installment_amount, sch.due_date 
        FROM `tabRE Payment Schedule` sch
        JOIN `tabRE Sales Agreement` sa ON sch.sales_agreement = sa.name
        WHERE sa.status = 'Confirmed' AND sch.status = 'Pending'
    """, as_dict=True)
    
    today = frappe.utils.nowdate()
    for sch in schedules:
        if targeted_doc_name and sch["name"] != targeted_doc_name:
            continue
            
        events = frappe.get_all("RE Billing Event", 
                                filters={"payment_schedule": sch["name"], "status": ["!=", "Cancelled"]}, 
                                fields=["name", "billing_amount", "idempotency_key"])
        
        if len(events) == 0 and sch["due_date"] <= today:
            log_finding("Orphan Payment Schedule", "Warning", "RE Payment Schedule", sch["name"],
                        "Has Billing Event", "Missing", active_signatures)
        elif len(events) > 1:
            log_finding("Duplicate Billing Event", "Critical", "RE Payment Schedule", sch["name"],
                        "1 Active Event", f"{len(events)} Active Events", active_signatures)
        elif len(events) == 1:
            if flt(events[0].billing_amount) != flt(sch["installment_amount"]):
                log_finding("Amount Mismatch", "Critical", "RE Billing Event", events[0].name,
                            str(sch["installment_amount"]), str(events[0].billing_amount), active_signatures)

    # 3. Orphan Sales Invoices
    shadow_items = frappe.get_all("RE Unit", filters={"shadow_item": ["is", "set"]}, pluck="shadow_item")
    if shadow_items:
        si_items = frappe.get_all("Sales Invoice Item", filters={"item_code": ["in", shadow_items], "docstatus": ["<", 2]}, pluck="parent")
        for inv_name in set(si_items):
            if targeted_doc_name and inv_name != targeted_doc_name:
                continue
                
            if frappe.db.count("RE Billing Event", {"erpnext_invoice_ref": inv_name, "status": ["!=", "Cancelled"]}) == 0:
                log_finding("Orphan Invoice", "Critical", "Sales Invoice", inv_name, "Has Billing Event", "Missing", active_signatures)

    # Scoped Auto-Resolution
    filters = {"status": ["in", ["Open", "Investigating"]]}
    if targeted_doc_name:
        filters["reference_document_name"] = targeted_doc_name
        
    open_findings = frappe.get_all("RE Integrity Finding", filters=filters, fields=["name", "finding_signature"])
    for f in open_findings:
        if f["finding_signature"] not in active_signatures:
            frappe.db.set_value("RE Integrity Finding", f["name"], "status", "Resolved")

@frappe.whitelist()
def run_integrity_audit(reference_type=None, reference_name=None):
    if not frappe.has_permission("RE Integrity Finding", "write"):
        raise frappe.PermissionError("You do not have permission to run integrity audits.")
    if reference_name:
        frappe.enqueue("kayanos.kayanos_core.financial_reconciliation.run_daily_integrity_audit", targeted_doc_name=reference_name, queue="long")
        return f"Audit queued for {reference_name}."
    else:
        frappe.enqueue("kayanos.kayanos_core.financial_reconciliation.run_daily_integrity_audit", queue="long")
        return "Full audit queued."
