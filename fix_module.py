import frappe
frappe.init(site='kayanos.localhost')
frappe.connect()

frappe.db.set_value('DocType', 'RE Project Profile', 'module', 'KayanOS Core')
frappe.db.commit()
