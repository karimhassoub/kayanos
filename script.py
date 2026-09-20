import frappe
def execute():
    if not frappe.db.exists('Workspace', 'KayanOS'):
        doc = frappe.new_doc('Workspace')
        doc.name = 'KayanOS'
        doc.title = 'KayanOS'
        doc.is_standard = 0
        doc.public = 1
        doc.is_hidden = 0
        doc.module = 'KayanOS Core'
        doc.append('roles', {'role': 'System Manager'})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print('KayanOS Workspace created!')
    else:
        print('Already exists!')

