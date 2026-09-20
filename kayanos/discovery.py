import frappe
def execute():
    print('=== PROJECT FIELDS ===')
    for df in frappe.get_meta('Project').fields:
        if df.fieldtype in ('Link', 'Select', 'Data', 'Check'):
            print(str(df.fieldname) + ' (' + str(df.fieldtype) + '): ' + str(df.options or ''))

    print('\n=== CRM DEAL FIELDS ===')
    for df in frappe.get_meta('CRM Deal').fields:
        if df.fieldtype in ('Link', 'Select', 'Data', 'Check', 'Dynamic Link'):
            print(str(df.fieldname) + ' (' + str(df.fieldtype) + '): ' + str(df.options or ''))
