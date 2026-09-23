import frappe
def run():
    has = frappe.get_meta("CRM Deal").has_field("erpnext_customer")
    print(f"Has field: {has}")
