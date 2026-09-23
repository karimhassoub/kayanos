import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters or not filters.get("customer"):
        return [], []

    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Transaction Type"), "fieldname": "transaction_type", "fieldtype": "Data", "width": 120},
        {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Dynamic Link", "options": "reference_type", "width": 150},
        {"label": _("Reference Type"), "fieldname": "reference_type", "fieldtype": "Data", "hidden": 1},
        {"label": _("Sales Agreement"), "fieldname": "sales_agreement", "fieldtype": "Link", "options": "RE Sales Agreement", "width": 150},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
        {"label": _("Invoiced Amount"), "fieldname": "invoiced_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Paid/Adjusted Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "options": "currency", "width": 120}
    ]

def get_data(filters):
    customer = filters.get("customer")
    company = filters.get("company")
    
    data = []
    
    company_filter = ""
    if company:
        company_filter = f"AND be.company = '{frappe.db.escape(company)}'"
        
    # 1. Get all Invoiced Billing Events
    events = frappe.db.sql(f"""
        SELECT 
            be.name, be.sales_agreement, be.erpnext_invoice_ref, be.currency,
            be.gross_invoiced_amount, be.returned_amount, 
            sch.due_date as posting_date
        FROM `tabRE Billing Event` be
        LEFT JOIN `tabRE Payment Schedule` sch ON be.payment_schedule = sch.name
        WHERE be.customer = %s AND be.status = 'Invoiced' {company_filter}
        ORDER BY sch.due_date ASC
    """, (customer,), as_dict=True)
    
    # Track the running balance
    balance = 0.0
    
    for ev in events:
        invoiced = flt(ev.get("gross_invoiced_amount", 0)) - flt(ev.get("returned_amount", 0))
        balance += invoiced
        data.append({
            "posting_date": ev.get("posting_date"),
            "transaction_type": "Billing Event",
            "reference": ev.get("name"),
            "reference_type": "RE Billing Event",
            "sales_agreement": ev.get("sales_agreement"),
            "currency": ev.get("currency"),
            "invoiced_amount": invoiced,
            "paid_amount": 0.0,
            "balance": balance
        })
        
        # 2. Find allocations for this invoice
        if ev.get("erpnext_invoice_ref"):
            # Payment Entries
            pe_company_filter = ""
            if company:
                pe_company_filter = f"AND pe.company = '{frappe.db.escape(company)}'"
                
            pes = frappe.db.sql(f"""
                SELECT pe.name, pe.posting_date, per.allocated_amount
                FROM `tabPayment Entry Reference` per
                JOIN `tabPayment Entry` pe ON per.parent = pe.name
                WHERE per.reference_doctype = 'Sales Invoice' 
                  AND per.reference_name = %s 
                  AND pe.docstatus = 1
                  {pe_company_filter}
            """, (ev["erpnext_invoice_ref"],), as_dict=True)
            
            for pe in pes:
                paid = flt(pe.get("allocated_amount", 0))
                balance -= paid
                data.append({
                    "posting_date": pe.get("posting_date"),
                    "transaction_type": "Payment Collection",
                    "reference": pe.get("name"),
                    "reference_type": "Payment Entry",
                    "sales_agreement": ev.get("sales_agreement"),
                    "currency": ev.get("currency"),
                    "invoiced_amount": 0.0,
                    "paid_amount": paid,
                    "balance": balance
                })
                
            # Journal Entries
            je_company_filter = ""
            if company:
                je_company_filter = f"AND je.company = '{frappe.db.escape(company)}'"
                
            jes = frappe.db.sql(f"""
                SELECT je.name, je.posting_date, jea.credit_in_account_currency
                FROM `tabJournal Entry Account` jea
                JOIN `tabJournal Entry` je ON jea.parent = je.name
                WHERE jea.reference_type = 'Sales Invoice' 
                  AND jea.reference_name = %s 
                  AND je.docstatus = 1
                  {je_company_filter}
            """, (ev["erpnext_invoice_ref"],), as_dict=True)
            
            for je in jes:
                adj = flt(je.get("credit_in_account_currency", 0))
                balance -= adj
                data.append({
                    "posting_date": je.get("posting_date"),
                    "transaction_type": "Adjustment",
                    "reference": je.get("name"),
                    "reference_type": "Journal Entry",
                    "sales_agreement": ev.get("sales_agreement"),
                    "currency": ev.get("currency"),
                    "invoiced_amount": 0.0,
                    "paid_amount": adj,
                    "balance": balance
                })

    # Tie-breaking logic: sort by date, then by transaction type to ensure deterministic running balance
    # Priority: Billing Event -> Payment -> Adjustment
    def get_sort_key(row):
        type_priority = {"Billing Event": 1, "Payment Collection": 2, "Adjustment": 3}
        # handle missing dates safely
        p_date = str(row["posting_date"]) if row["posting_date"] else "1970-01-01"
        return (p_date, type_priority.get(row["transaction_type"], 9), row["reference"])

    data.sort(key=get_sort_key)
    
    final_balance = 0.0
    for row in data:
        final_balance += flt(row["invoiced_amount"]) - flt(row["paid_amount"])
        row["balance"] = final_balance
        
    return data
