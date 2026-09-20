import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        'CRM Lead': [
            {'fieldname': 'kayanos_project', 'fieldtype': 'Link', 'label': 'KayanOS Project', 'options': 'Project', 'insert_after': 'status'}
        ],
        'CRM Deal': [
            {'fieldname': 'kayanos_project', 'fieldtype': 'Link', 'label': 'KayanOS Project', 'options': 'Project', 'insert_after': 'status'}
        ]
    }
    create_custom_fields(custom_fields)
    frappe.db.commit()
    print('Created custom fields manually')
