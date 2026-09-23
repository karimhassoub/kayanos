# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class REBillingEvent(Document):
    def validate(self):
        self.validate_agreement()
        self.validate_schedule()
        self.set_idempotency_key()
        self.check_immutability()

    def validate_agreement(self):
        if not self.sales_agreement:
            return
            
        agreement = frappe.get_cached_doc("RE Sales Agreement", self.sales_agreement)
        if agreement.status != "Confirmed":
            frappe.throw(_("Billing Event can only be created for Confirmed Sales Agreements. Current status: {0}").format(agreement.status))
            

        unit = agreement.unit
        agreement_company = None
        if unit:
            prop = frappe.db.get_value("RE Unit", unit, "property")
            if prop:
                phase = frappe.db.get_value("RE Property", prop, "phase")
                if phase:
                    project = frappe.db.get_value("RE Phase", phase, "project")
                    if project:
                        agreement_company = frappe.db.get_value("RE Project Profile", {"project": project}, "operating_company")
        
        if not self.company and agreement_company:
            self.company = agreement_company
        elif agreement_company and self.company != agreement_company:
            frappe.throw(_("Company mismatch. Event company '{0}' does not match Project company '{1}'").format(self.company, agreement_company))

            
        if not self.currency:
            self.currency = agreement.currency
        elif self.currency != agreement.currency:
            frappe.throw(_("Currency mismatch. Event currency '{0}' does not match Agreement currency '{1}'").format(self.currency, agreement.currency))

    def validate_schedule(self):
        if not self.payment_schedule:
            return
            
        schedule = frappe.get_doc("RE Payment Schedule", self.payment_schedule)
        
        # Security: schedule must belong to agreement
        if schedule.sales_agreement != self.sales_agreement:
            frappe.throw(_("Payment Schedule {0} does not belong to Sales Agreement {1}").format(self.payment_schedule, self.sales_agreement))
            
        # Amount must strictly come from authoritative source
        self.billing_amount = schedule.installment_amount

    def set_idempotency_key(self):
        if not self.sales_agreement or not self.payment_schedule or not self.trigger_type:
            return
        
        expected_key = f"{self.sales_agreement}-{self.payment_schedule}-{self.trigger_type}"
        if not self.idempotency_key:
            self.idempotency_key = expected_key
        elif self.idempotency_key != expected_key:
            frappe.throw(_("Idempotency key mismatch. Cannot modify identity fields."))

    def check_immutability(self):
        if not self.is_new() and self.db_get("status") == "Invoiced":
            # Core fields must not change
            immutable_fields = [
                "sales_agreement", "payment_schedule", "trigger_type",
                "billing_amount", "currency", "idempotency_key"
            ]
            for field in immutable_fields:
                if self.get(field) != self.db_get(field):
                    frappe.throw(_("Cannot modify {0} after Billing Event is Invoiced.").format(field))

    def on_trash(self):
        if self.status == "Invoiced":
            frappe.throw(_("Cannot delete an Invoiced Billing Event. It must be cancelled via authorized workflow instead."))
        if self.erpnext_invoice_ref:
            frappe.throw(_("Cannot delete Billing Event with external ERPNext reference {0}").format(self.erpnext_invoice_ref))
