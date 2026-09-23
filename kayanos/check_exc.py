import frappe
def run():
    print("Is subclass:", issubclass(frappe.exceptions.DuplicateEntryError, frappe.exceptions.UniqueValidationError))
