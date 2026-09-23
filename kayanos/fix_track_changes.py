import frappe
def execute():
    frappe.flags.in_test = False
    doc = frappe.get_doc("DocType", "RE Phase")
    doc.track_changes = 1
    doc.save(ignore_version=True)
