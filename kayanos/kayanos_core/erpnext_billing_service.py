# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def create_sales_invoice_from_billing_event(billing_event_name):
    """
    Phase 5I-B: ERPNext Invoice Integration (Real Estate Sales Billing ONLY)
    Creates a Sales Invoice from a Pending RE Billing Event.
    """
    # 1. Lock the Billing Event to prevent concurrent creation
    frappe.db.get_value("RE Billing Event", billing_event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", billing_event_name)
    
    # 2. Idempotency & Status Checks
    if event.erpnext_invoice_ref:
        if frappe.db.exists("Sales Invoice", event.erpnext_invoice_ref):
            return event.erpnext_invoice_ref
        else:
            frappe.throw(_("Billing Event contains stale ERPNext invoice reference. Manual intervention required."))
            
    if event.status == "Invoiced":
        frappe.throw(_("Billing Event is already marked as Invoiced but lacks a valid reference."))
        
    if event.status != "Pending" and event.status != "Failed":
        frappe.throw(_("Cannot create invoice. Billing Event status is {0}").format(event.status))
        
    # 3. Validate Agreement
    if not event.sales_agreement:
        frappe.throw(_("Missing Sales Agreement reference."))
    agreement = frappe.get_doc("RE Sales Agreement", event.sales_agreement)
    if agreement.status != "Confirmed":
        frappe.throw(_("Sales Agreement {0} is not Confirmed. Cannot bill.").format(agreement.name))
        
    # 4. Validate Payment Schedule
    if not event.payment_schedule:
        frappe.throw(_("Missing Payment Schedule reference."))
    schedule = frappe.get_doc("RE Payment Schedule", event.payment_schedule)
    if schedule.parent != agreement.name:
        frappe.throw(_("Payment Schedule {0} does not belong to Agreement {1}").format(schedule.name, agreement.name))
    if schedule.amount <= 0:
        frappe.throw(_("Cannot bill an installment with zero or negative amount ({0}).").format(schedule.amount))
        
    # 5. Validate Customer (Using mapping from Phase 5B)
    if not event.customer or not frappe.db.exists("Customer", event.customer):
        frappe.throw(_("Invalid Customer mapping. ERPNext Customer '{0}' does not exist.").format(event.customer))
        
    # 6. Validate Unit & Item
    if not event.unit:
        frappe.throw(_("Missing Unit mapping."))
    unit = frappe.get_doc("RE Unit", event.unit)
    if not unit.shadow_item or not frappe.db.exists("Item", unit.shadow_item):
        frappe.throw(_("Invalid Unit Item mapping. ERPNext Item '{0}' does not exist.").format(unit.shadow_item))
        
    # 7. Validate Company & Currency
    if not event.company or not frappe.db.exists("Company", event.company):
        frappe.throw(_("Invalid Company mapping. Company '{0}' does not exist.").format(event.company))
    if not event.currency:
        frappe.throw(_("Invalid currency mapping."))
        
    # 8. Invoice Creation
    # Note: KayanOS delegates VAT and Accounting entirely to ERPNext.
    # No VAT rules, taxes, or GL accounts are hard-coded here.
    try:
        si = frappe.new_doc("Sales Invoice")
        si.customer = event.customer
        si.company = event.company
        si.currency = event.currency
        
        # Set description per commercial domain
        description = (
            f"Real Estate Unit Sale Installment\n"
            f"Agreement: {agreement.name}\n"
            f"Unit: {unit.name}\n"
            f"Installment: {schedule.installment_sequence}"
        )
        
        si.append("items", {
            "item_code": unit.shadow_item,
            "qty": 1,
            "rate": event.billing_amount,
            "amount": event.billing_amount,
            "description": description
        })
        
        # Inherit ERPNext defaults (taxes, accounts) based on configuration
        si.set_missing_values()
        
        si.flags.ignore_permissions = True
        si.insert(ignore_permissions=True)
        si.submit()
        
    except Exception as e:
        # Atomic failure: The exception will rollback the transaction, 
        # ensuring the event stays Pending and no fake reference is recorded.
        frappe.throw(_("ERPNext Invoice creation failed due to configuration or integration error: {0}").format(str(e)))
        
    # 9. Status Transition
    event.db_set("erpnext_document_type", "Sales Invoice")
    event.db_set("erpnext_invoice_ref", si.name)
    event.db_set("status", "Invoiced")
    
    return si.name
