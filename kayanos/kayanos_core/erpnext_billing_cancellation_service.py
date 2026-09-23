# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def register_return_invoice(billing_event_name, return_invoice_ref):
    """
    Registers a submitted ERPNext Return Sales Invoice against an Invoiced Billing Event.
    """
    if not frappe.has_permission("RE Billing Event", "write", doc=billing_event_name):
        raise frappe.PermissionError(_("You do not have permission to modify this Billing Event."))
    # 1. Lock the Billing Event
    frappe.db.get_value("RE Billing Event", billing_event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", billing_event_name)
    
    if event.status != "Invoiced":
        frappe.throw(_("Cannot register a return for a Billing Event that is not Invoiced."))
        
    if not event.erpnext_invoice_ref:
        frappe.throw(_("Billing Event is missing the original ERPNext Invoice reference."))

    # 2. Idempotency Check
    existing_return = frappe.db.exists("RE Billing Event Return", {
        "parent": billing_event_name,
        "return_invoice_ref": return_invoice_ref
    })
    if existing_return:
        return  # Already registered

    # 3. Validate ERPNext Sales Invoice
    if not frappe.db.exists("Sales Invoice", return_invoice_ref):
        frappe.throw(_("Sales Invoice {0} does not exist.").format(return_invoice_ref))
        
    return_si = frappe.get_doc("Sales Invoice", return_invoice_ref)
    
    if return_si.docstatus != 1:
        frappe.throw(_("Return Sales Invoice {0} must be Submitted.").format(return_invoice_ref))
        
    if not return_si.is_return:
        frappe.throw(_("Sales Invoice {0} is not a Return invoice.").format(return_invoice_ref))
        
    if return_si.return_against != event.erpnext_invoice_ref:
        frappe.throw(_("Return Invoice {0} is against {1}, not the original invoice {2}.").format(
            return_invoice_ref, return_si.return_against, event.erpnext_invoice_ref
        ))
        
    # 4. Derive Amount (Returns usually have negative base_grand_total, so we take abs)
    return_amount = abs(return_si.base_grand_total)
    
    # 5. Over-return validation
    current_returned = event.returned_amount or 0.0
    new_total = current_returned + return_amount
    
    # Allow small float rounding leeway, but strictly validate against original amount
    if new_total > event.billing_amount + 0.01:
        frappe.throw(_("Total returned amount ({0}) would exceed original billing amount ({1}).").format(
            new_total, event.billing_amount
        ))
        
    # 6. Add child record
    event.append("returns", {
        "return_invoice_ref": return_invoice_ref,
        "returned_amount": return_amount,
        "return_date": return_si.posting_date
    })
    
    # 7. Update Event state
    event.returned_amount = new_total
    
    # Determine Settlement Status
    if abs(new_total - event.billing_amount) <= 0.01:
        event.settlement_status = "Fully Returned"
    else:
        event.settlement_status = "Partially Returned"
        
    # We do not automatically clear the financial_review_status, as Accounts might 
    # need to explicitly resolve the rest of the funds (e.g. penalty).
    # But if they want, they call resolve_financial_review explicitly.

    event.flags.ignore_permissions = True
    event.save(ignore_permissions=True)


@frappe.whitelist()
def resolve_financial_review(billing_event_name, reason, explanation=None):
    """
    Auditable resolution of a pending financial review.
    """
    if not frappe.has_permission("RE Billing Event", "write", doc=billing_event_name):
        raise frappe.PermissionError(_("You do not have permission to modify this Billing Event."))
    frappe.db.get_value("RE Billing Event", billing_event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", billing_event_name)
    
    if event.financial_review_status != "Pending Review":
        frappe.throw(_("Billing Event is not pending a financial review."))
        
    if reason == "Other" and not explanation:
        frappe.throw(_("An explanation is required when the reason is 'Other'."))
        
    event.financial_review_status = "Resolved"
    event.financial_review_resolution_reason = reason
    if explanation:
        event.financial_review_explanation = explanation
        
    event.financial_review_resolved_by = frappe.session.user
    event.financial_review_resolved_on = frappe.utils.now_datetime()
    
    event.flags.ignore_permissions = True
    event.save(ignore_permissions=True)


@frappe.whitelist()
def void_unpaid_billing_event(billing_event_name):
    """
    Natively cancels an unpaid ERPNext Sales Invoice and marks Billing Event as Cancelled.
    """
    if not frappe.has_permission("RE Billing Event", "write", doc=billing_event_name):
        raise frappe.PermissionError(_("You do not have permission to modify this Billing Event."))
    frappe.db.get_value("RE Billing Event", billing_event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", billing_event_name)
    
    if event.status == "Cancelled":
        return  # Already cancelled
        
    if event.status != "Invoiced" or not event.erpnext_invoice_ref:
        frappe.throw(_("Can only void an Invoiced event."))

    if not frappe.db.exists("Sales Invoice", event.erpnext_invoice_ref):
        # Stale reference, we can just mark cancelled? No, error out to be safe.
        frappe.throw(_("Original Sales Invoice {0} not found.").format(event.erpnext_invoice_ref))
        
    si = frappe.get_doc("Sales Invoice", event.erpnext_invoice_ref)
    
    if si.docstatus == 2:
        # Already cancelled in ERPNext, sync state
        pass
    else:
        # Check for payments
        if si.outstanding_amount < si.grand_total:
            frappe.throw(_("Invoice has linked payments. Cannot natively void. Use Credit Note instead."))
            
        try:
            si.cancel()
        except Exception as e:
            frappe.throw(_("Failed to natively void ERPNext Sales Invoice: {0}").format(str(e)))
            
    # Update Billing Event
    event.status = "Cancelled"
    
    # Auto-resolve review if it was pending
    if event.financial_review_status == "Pending Review" or event.financial_review_status == "Not Required":
        event.financial_review_status = "Resolved"
        event.financial_review_resolution_reason = "Natively Voided"
        event.financial_review_explanation = "Auto-resolved via void_unpaid_billing_event"
        event.financial_review_resolved_by = frappe.session.user
        event.financial_review_resolved_on = frappe.utils.now_datetime()
        
    event.flags.ignore_permissions = True
    event.save(ignore_permissions=True)


@frappe.whitelist()
def sync_returns(billing_event_name):
    """
    Iterates over registered returns. Removes any that have been cancelled in ERPNext.
    Recalculates totals.
    """
    if not frappe.has_permission("RE Billing Event", "write", doc=billing_event_name):
        raise frappe.PermissionError(_("You do not have permission to modify this Billing Event."))
    frappe.db.get_value("RE Billing Event", billing_event_name, "name", for_update=True)
    event = frappe.get_doc("RE Billing Event", billing_event_name)
    
    if not event.returns:
        return
        
    valid_returns = []
    total = 0.0
    
    changed = False
    for ret in event.returns:
        docstatus = frappe.db.get_value("Sales Invoice", ret.return_invoice_ref, "docstatus")
        if docstatus == 1:
            valid_returns.append(ret)
            total += ret.returned_amount
        else:
            changed = True
            
    if changed:
        event.returns = valid_returns
        event.returned_amount = total
        
        if total == 0:
            event.settlement_status = "Unsettled"
        elif abs(total - event.billing_amount) <= 0.01:
            event.settlement_status = "Fully Returned"
        else:
            event.settlement_status = "Partially Returned"
            
        event.flags.ignore_permissions = True
        event.save(ignore_permissions=True)
