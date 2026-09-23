# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def is_already_queued(doctype, name):
    """
    Checks if an Email Queue record already exists for the given document.
    This provides deduplication in case the background job is retried or triggered twice.
    """
    return frappe.db.exists("Email Queue", {
        "reference_doctype": doctype,
        "reference_name": name
    })

def send_reservation_confirmation(reservation_name):
    try:
        if is_already_queued("RE Unit Reservation", reservation_name):
            frappe.logger("kayanos").info(f"Reservation confirmation email already queued for {reservation_name}")
            return
            
        doc = frappe.get_doc("RE Unit Reservation", reservation_name)
        if not doc.customer:
            return
            
        customer = frappe.get_cached_doc("Customer", doc.customer)
        if not customer.email_id:
            frappe.logger("kayanos").info(f"No email for Customer {customer.name}. Skipping reservation email.")
            return
            
        context = {
            "customer_name": customer.customer_name,
            "unit": doc.unit,
            "reservation_name": doc.name,
            "expiry_time": frappe.utils.format_datetime(doc.expiry_time)
        }
        
        frappe.sendmail(
            recipients=[customer.email_id],
            subject=_("Your Reservation is Confirmed: {0}").format(doc.unit),
            template="reservation_confirmed",
            args=context,
            reference_doctype="RE Unit Reservation",
            reference_name=doc.name,
            now=False
        )
    except Exception as e:
        frappe.log_error(title="Reservation Email Queue Failed", message=str(e))

def send_agreement_confirmation(agreement_name):
    try:
        if is_already_queued("RE Sales Agreement", agreement_name):
            frappe.logger("kayanos").info(f"Agreement confirmation email already queued for {agreement_name}")
            return
            
        doc = frappe.get_doc("RE Sales Agreement", agreement_name)
        customer = frappe.get_cached_doc("Customer", doc.customer)
        if not customer.email_id:
            frappe.logger("kayanos").info(f"No email for Customer {customer.name}. Skipping agreement email.")
            return
            
        formatted_price = frappe.utils.fmt_money(doc.final_sale_price, currency=doc.currency)
        
        context = {
            "customer_name": customer.customer_name,
            "unit": doc.unit,
            "agreement_name": doc.name,
            "final_sale_price": formatted_price
        }
        
        frappe.sendmail(
            recipients=[customer.email_id],
            subject=_("Sales Agreement Confirmed: {0}").format(doc.unit),
            template="agreement_confirmed",
            args=context,
            reference_doctype="RE Sales Agreement",
            reference_name=doc.name,
            now=False
        )
    except Exception as e:
        frappe.log_error(title="Agreement Email Queue Failed", message=str(e))

def send_billing_invoiced(billing_event_name):
    try:
        if is_already_queued("RE Billing Event", billing_event_name):
            frappe.logger("kayanos").info(f"Billing invoice email already queued for {billing_event_name}")
            return
            
        doc = frappe.get_doc("RE Billing Event", billing_event_name)
        if not doc.erpnext_invoice_ref:
            return
            
        customer = frappe.get_cached_doc("Customer", doc.customer)
        if not customer.email_id:
            frappe.logger("kayanos").info(f"No email for Customer {customer.name}. Skipping billing email.")
            return
            
        formatted_amount = frappe.utils.fmt_money(doc.billing_amount, currency=doc.currency)
        
        context = {
            "customer_name": customer.customer_name,
            "unit": doc.unit,
            "invoice_ref": doc.erpnext_invoice_ref,
            "billed_amount": formatted_amount
        }
        
        frappe.sendmail(
            recipients=[customer.email_id],
            subject=_("Installment Invoiced: {0}").format(doc.erpnext_invoice_ref),
            template="billing_invoiced",
            args=context,
            reference_doctype="RE Billing Event",
            reference_name=doc.name,
            now=False
        )
    except Exception as e:
        frappe.log_error(title="Billing Email Queue Failed", message=str(e))
