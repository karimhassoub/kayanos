import frappe
from frappe import _
from frappe.utils import flt

def validate_sales_agreement_for_erpnext(agreement_name):
    """
    Validates that a Sales Agreement has all the required invariants
    to generate an ERPNext commercial/financial document (e.g. Sales Invoice).
    """
    # 1. Agreement exists and is Confirmed
    if not frappe.db.exists("RE Sales Agreement", agreement_name):
        frappe.throw(_("Sales Agreement {0} not found.").format(agreement_name))
        
    agr = frappe.get_doc("RE Sales Agreement", agreement_name)
    
    if agr.status != "Confirmed":
        frappe.throw(_("Sales Agreement {0} is not Confirmed. Current status: {1}").format(agreement_name, agr.status))
        
    # 2. ERPNext Customer must exist and be valid
    if not agr.customer:
        frappe.throw(_("Sales Agreement {0} is missing an ERPNext Customer.").format(agreement_name))
        
    if not frappe.db.exists("Customer", agr.customer):
        frappe.throw(_("The linked ERPNext Customer '{0}' does not exist in the system.").format(agr.customer))
        
    # 3. Unit and Item mapping
    if not agr.unit:
        frappe.throw(_("Sales Agreement is missing a Unit."))
        
    unit = frappe.get_doc("RE Unit", agr.unit)
    if not unit.shadow_item:
        frappe.throw(_("Unit {0} is not mapped to an ERPNext Item (shadow_item is missing).").format(unit.name))
        
    if not frappe.db.exists("Item", unit.shadow_item):
        frappe.throw(_("The mapped ERPNext Item '{0}' for Unit {1} does not exist.").format(unit.shadow_item, unit.name))
        
    # 4. Final sale price and currency
    if flt(agr.final_sale_price) <= 0:
        frappe.throw(_("Final Sale Price must be greater than zero."))
        
    if not agr.currency:
        frappe.throw(_("Sales Agreement is missing a Currency."))
        
    if not frappe.db.exists("Currency", agr.currency):
        frappe.throw(_("The Currency '{0}' does not exist in the system.").format(agr.currency))
        
    # 5. Payment Schedule consistency
    schedules = frappe.get_all(
        "RE Payment Schedule", 
        filters={"sales_agreement": agreement_name, "status": "Pending"},
        fields=["name", "installment_amount"]
    )
    
    if not schedules:
        frappe.throw(_("Sales Agreement has no Pending Payment Schedules."))
        
    total_schedule_amount = sum(flt(s.installment_amount) for s in schedules)
    
    # We round to 2 decimal places or to the currency precision for comparison
    precision = frappe.db.get_single_value("System Settings", "currency_precision") or 2
    if flt(total_schedule_amount, precision) != flt(agr.final_sale_price, precision):
        frappe.throw(_("Payment Schedule total ({0}) does not match Final Sale Price ({1}).").format(total_schedule_amount, agr.final_sale_price))
        
    # 6. Operating Company Validation
    property_doc = frappe.get_doc("RE Property", unit.property)
    phase = frappe.get_doc("RE Phase", property_doc.phase)
    project_name = phase.project
    
    profile_name = frappe.db.get_value("RE Project Profile", {"project": project_name}, "name")
    if not profile_name:
        frappe.throw(_("No RE Project Profile found for Project '{0}'.").format(project_name))
        
    company = frappe.db.get_value("RE Project Profile", profile_name, "operating_company")
    if not company:
        frappe.throw(_("Operating Company is not set in RE Project Profile for Project '{0}'.").format(project_name))
        
    if not frappe.db.exists("Company", company):
        frappe.throw(_("The Operating Company '{0}' does not exist in the system.").format(company))
        
    return agr, unit, company


def get_sales_agreement_commercial_payload(agreement_name):
    """
    Returns an authoritative, server-derived dictionary representing the
    financial obligations of a Sales Agreement. 
    This payload is fully verified and ready for an accounting module
    to safely consume (e.g. to generate a Sales Invoice).
    """
    agr, unit, company = validate_sales_agreement_for_erpnext(agreement_name)
    
    # Fetch all schedules to pass along
    schedules = frappe.get_all(
        "RE Payment Schedule", 
        filters={"sales_agreement": agreement_name, "status": "Pending"},
        fields=["name", "installment_sequence", "installment_type", "due_date", "payment_percentage", "installment_amount"],
        order_by="installment_sequence asc"
    )
    
    payload = {
        "sales_agreement": agr.name,
        "customer": agr.customer,
        "item_code": unit.shadow_item,
        "company": company,
        "currency": agr.currency,
        "unit_price": flt(agr.unit_price),
        "discount_amount": flt(agr.discount),
        "final_sale_price": flt(agr.final_sale_price),
        "payment_schedule": schedules
    }
    
    return payload
