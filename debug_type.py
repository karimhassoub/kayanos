import sys
import frappe
frappe.init(site='kayanos.localhost')
frappe.connect()
print('Developer Type:', type(frappe.get_doc({'doctype': 'RE Project Profile'}).developer_type))
