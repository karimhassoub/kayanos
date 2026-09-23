import frappe

def create_doctype(name, module, fields, **kwargs):
    if frappe.db.exists('DocType', name):
        doc = frappe.get_doc('DocType', name)
    else:
        doc = frappe.new_doc('DocType')
        doc.name = name
    
    doc.update({
        'module': module,
        'custom': 0,
        'fields': fields
    })
    doc.update(kwargs)
    doc.flags.ignore_permissions = True
    doc.save(ignore_version=True)
    return doc

def execute():
    frappe.flags.in_test = False
    
    # 1. Setup Types
    create_doctype('RE Phase Type', 'KayanOS Core', [
        {'fieldname': 'type_name', 'fieldtype': 'Data', 'label': 'Type Name', 'reqd': 1, 'unique': 1},
        {'fieldname': 'description', 'fieldtype': 'Small Text', 'label': 'Description'}
    ], naming_rule='By fieldname', autoname='field:type_name')
    
    create_doctype('RE Property Type', 'KayanOS Core', [
        {'fieldname': 'type_name', 'fieldtype': 'Data', 'label': 'Type Name', 'reqd': 1, 'unique': 1}
    ], naming_rule='By fieldname', autoname='field:type_name')
    
    create_doctype('RE Unit Type', 'KayanOS Core', [
        {'fieldname': 'type_name', 'fieldtype': 'Data', 'label': 'Type Name', 'reqd': 1, 'unique': 1},
        {'fieldname': 'category', 'fieldtype': 'Select', 'label': 'Category', 'options': 'Residential\nCommercial\nLand\nOther'}
    ], naming_rule='By fieldname', autoname='field:type_name')
    
    # 2. Child Table
    create_doctype('RE Unit Component', 'KayanOS Core', [
        {'fieldname': 'component_type', 'fieldtype': 'Data', 'label': 'Component Type', 'reqd': 1},
        {'fieldname': 'component_number', 'fieldtype': 'Data', 'label': 'Component Number'},
        {'fieldname': 'description', 'fieldtype': 'Data', 'label': 'Description'},
        {'fieldname': 'area', 'fieldtype': 'Float', 'label': 'Area'}
    ], istable=1)
    
    # 3. Core Hierarchy
    create_doctype('RE Phase', 'KayanOS Core', [
        {'fieldname': 'phase_name', 'fieldtype': 'Data', 'label': 'Phase Name', 'reqd': 1},
        {'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'label': 'Project', 'reqd': 1, 'in_list_view': 1},
        {'fieldname': 'phase_type', 'fieldtype': 'Link', 'options': 'RE Phase Type', 'label': 'Phase Type'},
        {'fieldname': 'status', 'fieldtype': 'Select', 'label': 'Status', 'options': 'Draft\nActive\nInactive', 'default': 'Draft', 'in_list_view': 1},
        {'fieldname': 'developer_type', 'fieldtype': 'Select', 'label': 'Developer Type', 'options': 'Internal\nExternal', 'default': 'Internal'},
        {'fieldname': 'external_developer_type', 'fieldtype': 'Select', 'label': 'External Developer Type', 'options': '\nCustomer\nSupplier\nCompany', 'depends_on': 'eval:doc.developer_type=="External"'},
        {'fieldname': 'external_developer', 'fieldtype': 'Dynamic Link', 'options': 'external_developer_type', 'label': 'External Developer', 'depends_on': 'eval:doc.developer_type=="External"'},
        {'fieldname': 'sales_authorized', 'fieldtype': 'Check', 'label': 'Sales Authorized', 'default': 0},
        {'fieldname': 'construction_responsible', 'fieldtype': 'Data', 'label': 'Construction Responsible'}
    ], naming_rule='Expression', autoname='format:{project}-{phase_name}', permissions=[{'role': 'Real Estate Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1}])

    create_doctype('RE Property', 'KayanOS Core', [
        {'fieldname': 'property_name', 'fieldtype': 'Data', 'label': 'Property Name', 'reqd': 1},
        {'fieldname': 'property_code', 'fieldtype': 'Data', 'label': 'Property Code'},
        {'fieldname': 'phase', 'fieldtype': 'Link', 'options': 'RE Phase', 'label': 'Phase', 'reqd': 1, 'in_list_view': 1},
        {'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'label': 'Project', 'read_only': 1, 'in_list_view': 1},
        {'fieldname': 'property_type', 'fieldtype': 'Link', 'options': 'RE Property Type', 'label': 'Property Type'},
        {'fieldname': 'status', 'fieldtype': 'Select', 'label': 'Status', 'options': 'Draft\nActive\nInactive', 'default': 'Draft'}
    ], naming_rule='Expression', autoname='format:{phase}-{property_name}', permissions=[{'role': 'Real Estate Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1}])

    create_doctype('RE Unit', 'KayanOS Core', [
        {'fieldname': 'unit_number', 'fieldtype': 'Data', 'label': 'Unit Number', 'reqd': 1},
        {'fieldname': 'property', 'fieldtype': 'Link', 'options': 'RE Property', 'label': 'Property', 'reqd': 1, 'in_list_view': 1},
        {'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'label': 'Project', 'read_only': 1, 'in_list_view': 1},
        {'fieldname': 'unit_type', 'fieldtype': 'Link', 'options': 'RE Unit Type', 'label': 'Unit Type'},
        {'fieldname': 'lifecycle_status', 'fieldtype': 'Select', 'label': 'Lifecycle Status', 'options': 'Draft\nActive\nInactive', 'default': 'Draft', 'in_list_view': 1},
        {'fieldname': 'availability_status', 'fieldtype': 'Select', 'label': 'Availability Status', 'options': 'Not Released\nAvailable\nWithheld\nReserved\nSold', 'default': 'Not Released', 'in_list_view': 1},
        {'fieldname': 'built_up_area', 'fieldtype': 'Float', 'label': 'Built Up Area'},
        {'fieldname': 'price', 'fieldtype': 'Currency', 'label': 'Price'},
        {'fieldname': 'shadow_item', 'fieldtype': 'Link', 'options': 'Item', 'label': 'Shadow Item', 'read_only': 1, 'unique': 1},
        {'fieldname': 'included_components', 'fieldtype': 'Table', 'options': 'RE Unit Component', 'label': 'Included Components'}
    ], naming_rule='Expression', autoname='format:{property}-{unit_number}', permissions=[{'role': 'Real Estate Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1}])

