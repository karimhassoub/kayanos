import frappe
from frappe.exceptions import LinkExistsError, ValidationError
import json

def execute():
    frappe.flags.in_test = True
    print('=== SECTION 2A: Project Deletion Integrity ===')
    # Get/Create company
    company = frappe.get_all('Company', limit=1)[0].name
    
    # 1 & 2
    proj = frappe.get_doc({'doctype': 'Project', 'project_name': 'DEL-TEST-PROJ', 'company': company}).insert(ignore_permissions=True)
    prof = frappe.get_doc({'doctype': 'RE Project Profile', 'project': proj.name, 'operating_company': company, 'ownership_type': 'Internal'}).insert(ignore_permissions=True)
    print(f'1,2. Created Project {proj.name} and Profile {prof.name}')
    
    # 3 & 4
    try:
        frappe.delete_doc('Project', proj.name)
        print('FAILED: Project was deleted!')
    except LinkExistsError as e:
        print(f'3,4. Caught expected LinkExistsError: {e}')
    
    # 5
    assert frappe.db.exists('Project', proj.name)
    print(f'5. Confirmed Project {proj.name} still exists.')
    
    # 6 & 7
    frappe.delete_doc('RE Project Profile', prof.name)
    print('6. Removed RE Project Profile.')
    frappe.delete_doc('Project', proj.name)
    print(f'7. Confirmed Project {proj.name} successfully deleted after Profile removal.')

    print('\n=== SECTION 2B: CRM Lead to Deal Conversion ===')
    from crm.fcrm.doctype.crm_lead.crm_lead import convert_to_deal
    # 1 & 2
    proj2 = frappe.get_doc({'doctype': 'Project', 'project_name': 'CONV-TEST-PROJ', 'company': company}).insert(ignore_permissions=True)
    lead_with_proj = frappe.get_doc({'doctype': 'CRM Lead', 'first_name': 'Lead With Proj', 'kayanos_project': proj2.name}).insert(ignore_permissions=True)
    print(f'1,2. Created Lead {lead_with_proj.name} with project {proj2.name}')
    
    # 3, 4, 5
    deal1_id = convert_to_deal(lead_with_proj.name)
    deal1 = frappe.get_doc('CRM Deal', deal1_id)
    print(f'3,4,5. Converted to Deal {deal1.name}. Deal kayanos_project = {deal1.kayanos_project} (Expected: {proj2.name})')
    
    # 6, 7
    lead_no_proj = frappe.get_doc({'doctype': 'CRM Lead', 'first_name': 'Lead No Proj'}).insert(ignore_permissions=True)
    deal2_id = convert_to_deal(lead_no_proj.name)
    deal2 = frappe.get_doc('CRM Deal', deal2_id)
    print(f'6,7. Created Lead {lead_no_proj.name} without project. Converted to Deal {deal2.name}. kayanos_project = {deal2.kayanos_project} (Expected: None)')

    print('\n=== SECTION 5: DocType Metadata ===')
    meta_prof = frappe.get_meta('RE Project Profile')
    f_proj = meta_prof.get_field('project')
    print(f'RE Project Profile -> project: type={f_proj.fieldtype}, reqd={f_proj.reqd}, unique={f_proj.unique}')
    print(f'RE Project Profile Module: {meta_prof.module}')
    print('RE Project Profile Permissions:')
    for p in meta_prof.permissions:
        print(f' - Role: {p.role}, read={p.read}, write={p.write}, create={p.create}')
    
    meta_lead = frappe.get_meta('CRM Lead')
    f_lead = meta_lead.get_field('kayanos_project')
    print(f'CRM Lead -> kayanos_project: type={f_lead.fieldtype}, options={f_lead.options}, reqd={f_lead.reqd}')
    
    meta_deal = frappe.get_meta('CRM Deal')
    f_deal = meta_deal.get_field('kayanos_project')
    print(f'CRM Deal -> kayanos_project: type={f_deal.fieldtype}, options={f_deal.options}, reqd={f_deal.reqd}')

    print('\n=== SECTION 7: Security (Permissions) ===')
    try:
        frappe.set_user('Guest')
        doc = frappe.get_doc({'doctype': 'RE Project Profile', 'project': proj2.name, 'operating_company': company, 'ownership_type': 'Internal'})
        doc.insert()
        print('FAILED: Guest was able to insert!')
    except frappe.exceptions.PermissionError:
        print('Caught expected PermissionError for unauthorized user (Guest)')
    finally:
        frappe.set_user('Administrator')

