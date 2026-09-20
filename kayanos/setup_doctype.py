import frappe

def execute():
    frappe.flags.in_test = True
    
    # Create Role
    if not frappe.db.exists('Role', 'Real Estate Manager'):
        doc = frappe.new_doc('Role')
        doc.role_name = 'Real Estate Manager'
        doc.desk_access = 1
        doc.insert(ignore_permissions=True)

    # Create DocType
    if not frappe.db.exists('DocType', 'RE Project Profile'):
        doc = frappe.new_doc('DocType')
        doc.name = 'RE Project Profile'
        doc.module = 'Real Estate'
        doc.custom = 0
        doc.autoname = 'format:RE-PROJ-{project}'
        doc.naming_rule = 'Expression'
        
        fields = [
            {'fieldname': 'project', 'label': 'Project', 'fieldtype': 'Link', 'options': 'Project', 'reqd': 1, 'unique': 1, 'in_list_view': 1},
            {'fieldname': 'operating_company', 'label': 'Operating Company', 'fieldtype': 'Link', 'options': 'Company', 'reqd': 1, 'in_list_view': 1},
            {'fieldname': 'ownership_type', 'label': 'Ownership Type', 'fieldtype': 'Select', 'options': 'Internal\nExternal', 'reqd': 1},
            {'fieldname': 'developer_type', 'label': 'Developer Type', 'fieldtype': 'Select', 'options': '\nCustomer\nSupplier\nCompany', 'depends_on': 'eval:doc.ownership_type=="External"'},
            {'fieldname': 'external_developer', 'label': 'External Developer', 'fieldtype': 'Dynamic Link', 'options': 'developer_type', 'depends_on': 'eval:doc.ownership_type=="External"'},
            {'fieldname': 'sales_authorized', 'label': 'Sales Authorized', 'fieldtype': 'Check', 'default': '0'},
            {'fieldname': 'construction_responsible', 'label': 'Construction Responsible', 'fieldtype': 'Check', 'default': '0'}
        ]
        
        for f in fields:
            doc.append('fields', f)
            
        doc.append('permissions', {
            'role': 'Real Estate Manager',
            'read': 1, 'write': 1, 'create': 1, 'delete': 1,
            'export': 1, 'report': 1, 'share': 1
        })
        
        doc.insert(ignore_permissions=True)
        print('Created RE Project Profile')
    else:
        print('Already exists!')
