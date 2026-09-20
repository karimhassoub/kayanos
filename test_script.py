import frappe
frappe.init(site='kayanos.localhost')
frappe.connect()

doc = frappe.get_doc({
    'doctype': 'RE Project Profile',
    'project': 'Test Proj',
    'operating_company': 'Test Co',
    'ownership_type': 'Internal'
})
doc.validate()
