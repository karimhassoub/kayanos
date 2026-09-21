import frappe
from frappe import _

def get_or_create_customer(crm_deal_name):
    """
    KayanOS Phase 5B: Controlled Customer Bridge
    Maps a CRM Deal (and its Organization/Lead) to an ERPNext Customer explicitly.
    Returns the Customer name.
    """
    if not frappe.db.exists("CRM Deal", crm_deal_name):
        frappe.throw(_("CRM Deal {0} not found").format(crm_deal_name))
        
    # Lock the Deal to prevent concurrent customer creation for the same deal
    frappe.db.get_value("CRM Deal", crm_deal_name, "name", for_update=True)
    deal = frappe.get_doc("CRM Deal", crm_deal_name)
    
    # 1. Check if Deal already has erpnext_customer linked
    if deal.meta.has_field("erpnext_customer") and deal.get("erpnext_customer"):
        if frappe.db.exists("Customer", deal.erpnext_customer):
            return deal.erpnext_customer
        else:
            # Stale link fails safely rather than creating a new disjointed customer
            frappe.throw(_("The linked ERPNext Customer '{0}' no longer exists in the system. Please clear the link and try again.").format(deal.erpnext_customer))
            
    # 2. Map identity
    if deal.organization:
        customer_name = deal.organization
        customer_type = "Company"
    elif deal.lead_name:
        customer_name = deal.lead_name
        customer_type = "Individual"
    else:
        frappe.throw(_("CRM Deal must have an Organization or Lead Name to create a Customer"))
        
    # 3. Prevent silent linkage to same-name but potentially different identity
    existing_customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
    if existing_customer:
        frappe.throw(_("A Customer with the name '{0}' already exists. To prevent associating this Deal with the wrong identity, please link the customer manually in the CRM Deal if it is the same entity, or rename the CRM Organization/Lead.").format(customer_name))
        
    # 4. Create new customer natively in ERPNext
    try:
        customer = frappe.new_doc("Customer")
        customer.customer_name = customer_name
        customer.customer_type = customer_type
        
        # Map territory if exists
        if deal.get("territory") and frappe.db.exists("Territory", deal.territory):
            customer.territory = deal.territory
            
        # Customer Group is often required by ERPNext
        default_customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
        if not default_customer_group:
            default_customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
            
        if default_customer_group:
            customer.customer_group = default_customer_group
            
        customer.flags.ignore_mandatory = True
        customer.insert(ignore_permissions=True)
        
        if deal.meta.has_field("erpnext_customer"):
            deal.db_set("erpnext_customer", customer.name)
            
        return customer.name
    except Exception as e:
        frappe.db.rollback()
        raise e
