import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 150},
        {"label": _("Sales Agreement"), "fieldname": "sales_agreement", "fieldtype": "Link", "options": "RE Sales Agreement", "width": 150},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
        {"label": _("Contract Value"), "fieldname": "contract_value", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Total Invoiced"), "fieldname": "total_invoiced", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Total Collected"), "fieldname": "total_collected", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Total Returned"), "fieldname": "total_returned", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": _("Total Outstanding"), "fieldname": "total_outstanding", "fieldtype": "Currency", "options": "currency", "width": 120},
    ]

def get_data(filters):
    conditions = "status = 'Confirmed'"
    
    if filters and filters.get("company"):
        conditions += f" AND company = '{frappe.db.escape(filters.get('company'))}'"
        
    if filters and filters.get("customer"):
        conditions += f" AND customer = '{frappe.db.escape(filters.get('customer'))}'"
    
    agreements = frappe.db.sql(f"""
        SELECT name as sales_agreement, customer, base_total_amount as contract_value, currency
        FROM `tabRE Sales Agreement`
        WHERE {conditions}
    """, as_dict=True)

    data = []
    
    for ag in agreements:
        # Aggregate billing events for this agreement
        events = frappe.db.sql("""
            SELECT 
                SUM(gross_invoiced_amount) as invoiced,
                SUM(cash_allocated + adjustment_allocated) as collected,
                SUM(returned_amount) as returned,
                SUM(projected_balance) as outstanding
            FROM `tabRE Billing Event`
            WHERE sales_agreement = %s AND status = 'Invoiced'
        """, (ag["sales_agreement"],), as_dict=True)
        
        events_row = events[0] if events else {}
        
        row = {
            "project": "Default Project", # Mock until multi-project mapping is needed
            "sales_agreement": ag["sales_agreement"],
            "customer": ag["customer"],
            "currency": ag["currency"],
            "contract_value": ag.get("contract_value", 0.0) or 0.0,
            "total_invoiced": events_row.get("invoiced", 0.0) or 0.0,
            "total_collected": events_row.get("collected", 0.0) or 0.0,
            "total_returned": events_row.get("returned", 0.0) or 0.0,
            "total_outstanding": events_row.get("outstanding", 0.0) or 0.0
        }
        data.append(row)
        
    return data
