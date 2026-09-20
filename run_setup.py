import sys
import frappe
frappe.init(site='kayanos.localhost')
frappe.connect()

from kayanos.setup_doctype import execute
execute()
frappe.db.commit()
