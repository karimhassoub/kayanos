import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Billing Event"), "fieldname": "name", "fieldtype": "Link", "options": "RE Billing Event", "width": 150},
        {"label": _("Sales Agreement"), "fieldname": "sales_agreement", "fieldtype": "Link", "options": "RE Sales Agreement", "width": 150},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("ERPNext Invoice"), "fieldname": "erpnext_invoice_ref", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("Collection Status"), "fieldname": "collection_status", "fieldtype": "Data", "width": 120},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
        {"label": _("Gross Invoiced"), "fieldname": "gross_invoiced_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Returned"), "fieldname": "returned_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Cash Allocated"), "fieldname": "cash_allocated", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Adjustment Allocated"), "fieldname": "adjustment_allocated", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"label": _("Projected Balance"), "fieldname": "projected_balance", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100}
    ]

def get_data(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append(f"be.company = '{frappe.db.escape(filters.get('company'))}'")
    if filters.get("customer"):
        conditions.append(f"be.customer = '{frappe.db.escape(filters.get('customer'))}'")
    if filters.get("sales_agreement"):
        conditions.append(f"be.sales_agreement = '{frappe.db.escape(filters.get('sales_agreement'))}'")
    if filters.get("collection_status"):
        conditions.append(f"be.collection_status = '{frappe.db.escape(filters.get('collection_status'))}'")
        
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # We join with RE Payment Schedule to get the due_date for aging
    sql = f"""
        SELECT 
            be.name, be.sales_agreement, be.customer, be.erpnext_invoice_ref,
            be.status, be.collection_status, be.currency,
            be.gross_invoiced_amount, be.returned_amount, be.cash_allocated,
            be.adjustment_allocated, be.projected_balance,
            sch.due_date
        FROM `tabRE Billing Event` be
        LEFT JOIN `tabRE Payment Schedule` sch ON be.payment_schedule = sch.name
        WHERE {where_clause}
        ORDER BY sch.due_date ASC
    """
    
    return frappe.db.sql(sql, as_dict=True)
