import frappe
frappe.init(site='kayanos.localhost')
frappe.connect()

for p in frappe.get_all('Project', filters={'project_name': ['like', 'Test Canonical Project%']}):
    frappe.delete_doc('Project', p.name, force=1)
for p in frappe.get_all('Project', filters={'project_name': ['like', 'Proj %']}):
    frappe.delete_doc('Project', p.name, force=1)
frappe.db.commit()
