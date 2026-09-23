import frappe

def create_doctypes():
    # 1. RE Cancellation Policy
    if not frappe.db.exists('DocType', 'RE Cancellation Policy'):
        doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'RE Cancellation Policy',
            'module': 'KayanOS Core',
            'custom': 0,
            'istable': 0,
            'issingle': 0,
            'is_submittable': 0,
            'autoname': 'field:policy_name',
            'fields': [
                {'fieldname': 'policy_name', 'fieldtype': 'Data', 'label': 'Policy Name', 'reqd': 1, 'unique': 1},
                {'fieldname': 'cancel_future_installments', 'fieldtype': 'Check', 'label': 'Cancel Future Installments', 'default': '1'},
                {'fieldname': 'void_unpaid_invoices', 'fieldtype': 'Check', 'label': 'Void Unpaid Invoices', 'default': '1'},
                {'fieldname': 'refund_paid_amounts', 'fieldtype': 'Check', 'label': 'Refund Paid Amounts', 'default': '1'},
                {'fieldname': 'cancellation_fee_percentage', 'fieldtype': 'Percent', 'label': 'Cancellation Fee (%)'},
                {'fieldname': 'cancellation_fee_amount', 'fieldtype': 'Currency', 'label': 'Cancellation Fee (Fixed Amount)'},
                {'fieldname': 'forfeit_reservation_amount', 'fieldtype': 'Check', 'label': 'Forfeit Reservation Amount'},
                {'fieldname': 'cancellation_fee_item', 'fieldtype': 'Link', 'options': 'Item', 'label': 'Cancellation Fee Item'}
            ],
            'permissions': [
                {'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1},
                {'role': 'Real Estate Manager', 'read': 1},
                {'role': 'Accounts Manager', 'read': 1},
                {'role': 'Sales Manager', 'read': 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print('Created RE Cancellation Policy')

    # 2. RE Agreement Cancellation
    if not frappe.db.exists('DocType', 'RE Agreement Cancellation'):
        doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'RE Agreement Cancellation',
            'module': 'KayanOS Core',
            'custom': 0,
            'istable': 0,
            'issingle': 0,
            'is_submittable': 1,
            'autoname': 'naming_series:',
            'fields': [
                {'fieldname': 'naming_series', 'fieldtype': 'Select', 'label': 'Series', 'options': 'ACC-CANC-.YYYY.-'},
                
                {'fieldname': 'section_core', 'fieldtype': 'Section Break', 'label': 'Core References'},
                {'fieldname': 'sales_agreement', 'fieldtype': 'Link', 'options': 'RE Sales Agreement', 'label': 'Sales Agreement', 'reqd': 1},
                {'fieldname': 'customer', 'fieldtype': 'Link', 'options': 'Customer', 'label': 'Customer', 'read_only': 1, 'fetch_from': 'sales_agreement.customer'},
                {'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'label': 'Project', 'read_only': 1, 'fetch_from': 'sales_agreement.project'},
                {'fieldname': 'cancellation_reason', 'fieldtype': 'Small Text', 'label': 'Cancellation Reason', 'reqd': 1},
                {'fieldname': 'cancellation_policy', 'fieldtype': 'Link', 'options': 'RE Cancellation Policy', 'label': 'Applied Cancellation Policy', 'read_only': 1},
                
                {'fieldname': 'section_calc', 'fieldtype': 'Section Break', 'label': 'Calculation Snapshot'},
                {'fieldname': 'gross_paid_amount', 'fieldtype': 'Currency', 'label': 'Gross Paid Amount', 'read_only': 1},
                {'fieldname': 'gross_unpaid_invoiced_amount', 'fieldtype': 'Currency', 'label': 'Gross Unpaid Invoiced Amount', 'read_only': 1},
                {'fieldname': 'calculated_cancellation_fee', 'fieldtype': 'Currency', 'label': 'Calculated Cancellation Fee', 'read_only': 1},
                {'fieldname': 'calculated_reservation_forfeiture', 'fieldtype': 'Currency', 'label': 'Reservation Forfeiture', 'read_only': 1},
                {'fieldname': 'total_approved_deductions', 'fieldtype': 'Currency', 'label': 'Total Approved Deductions', 'read_only': 1},
                {'fieldname': 'net_approved_refund', 'fieldtype': 'Currency', 'label': 'Net Approved Refund', 'read_only': 1},
                
                {'fieldname': 'section_exec', 'fieldtype': 'Section Break', 'label': 'Financial Execution'},
                {'fieldname': 'execution_status', 'fieldtype': 'Select', 'label': 'Execution Status', 'options': 'Pending\nPartially Executed\nReconciled\nCompleted\nFailed\nFinance Exception', 'default': 'Pending', 'read_only': 1},
                {'fieldname': 'cancellation_fee_invoice_ref', 'fieldtype': 'Link', 'options': 'Sales Invoice', 'label': 'Fee Invoice Ref', 'read_only': 1},
                {'fieldname': 'refund_payment_entry_ref', 'fieldtype': 'Link', 'options': 'Payment Entry', 'label': 'Refund Payment Entry Ref', 'read_only': 1},
                
                {'fieldname': 'amended_from', 'fieldtype': 'Link', 'options': 'RE Agreement Cancellation', 'label': 'Amended From', 'read_only': 1, 'print_hide': 1}
            ],
            'permissions': [
                {'role': 'Sales Manager', 'read': 1, 'write': 1, 'create': 1},
                {'role': 'Real Estate Manager', 'read': 1, 'write': 1, 'submit': 1},
                {'role': 'Accounts Manager', 'read': 1, 'write': 1, 'submit': 1},
                {'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1, 'cancel': 1, 'amend': 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print('Created RE Agreement Cancellation')
    else:
        print('RE Agreement Cancellation already exists')

def create_fields():
    try:
        from frappe.custom.doctype.property_setter.property_setter import make_property_setter
        
        # 1. Project Profile
        if not frappe.db.exists('Custom Field', {'dt': 'RE Project Profile', 'fieldname': 'default_cancellation_policy'}):
            frappe.get_doc({
                'doctype': 'Custom Field',
                'dt': 'RE Project Profile',
                'fieldname': 'default_cancellation_policy',
                'fieldtype': 'Link',
                'options': 'RE Cancellation Policy',
                'label': 'Default Cancellation Policy',
                'insert_after': 'project'
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            print('Added field to RE Project Profile')

        # 2. Sales Agreement
        if not frappe.db.exists('Custom Field', {'dt': 'RE Sales Agreement', 'fieldname': 'applied_cancellation_policy'}):
            frappe.get_doc({
                'doctype': 'Custom Field',
                'dt': 'RE Sales Agreement',
                'fieldname': 'applied_cancellation_policy',
                'fieldtype': 'Link',
                'options': 'RE Cancellation Policy',
                'label': 'Applied Cancellation Policy',
                'insert_after': 'status'
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            print('Added field to RE Sales Agreement')
            
    except Exception as e:
        print('Error creating fields:', e)

if __name__ == '__main__':
    frappe.init(site='kayanos.localhost', sites_path='./sites')
    frappe.connect()
    create_doctypes()
    create_fields()
