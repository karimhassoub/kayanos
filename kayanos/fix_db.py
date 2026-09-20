import frappe
def execute():
    try:
        from crm.fcrm.doctype.crm_lead.crm_lead import convert_to_deal
        print('Import successful from crm.fcrm.doctype')
    except Exception as e:
        print('Error:', e)
