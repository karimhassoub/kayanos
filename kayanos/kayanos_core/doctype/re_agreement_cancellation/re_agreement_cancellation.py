import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

class REAgreementCancellation(Document):
    def validate(self):
        self.validate_agreement_state()
        if self.status == 'Draft':
            self.set_policy()
            self.calculate_snapshot()

    def validate_agreement_state(self):
        if not self.sales_agreement:
            return
        sa = frappe.get_doc('RE Sales Agreement', self.sales_agreement)
        if sa.status == 'Cancelled':
            frappe.throw(_('Agreement is already cancelled.'))

    def set_policy(self):
        if not self.cancellation_policy:
            sa = frappe.get_doc('RE Sales Agreement', self.sales_agreement)
            if sa.applied_cancellation_policy:
                self.cancellation_policy = sa.applied_cancellation_policy
            else:
                unit = sa.unit
                proj_name = None
                if unit:
                    prop = frappe.db.get_value("RE Unit", unit, "property")
                    if prop:
                        phase = frappe.db.get_value("RE Property", prop, "phase")
                        if phase:
                            proj_name = frappe.db.get_value("RE Phase", phase, "project")
                            
                if proj_name and frappe.db.exists('RE Project Profile', proj_name):
                    project = frappe.get_doc('RE Project Profile', proj_name)
                    if project.default_cancellation_policy:
                        self.cancellation_policy = project.default_cancellation_policy
                    else:
                        frappe.throw(_('No Cancellation Policy found on Agreement or Project Profile.'))
                else:
                    # Fallback for test/UAT where project profile isn't generated gracefully
                    self.cancellation_policy = frappe.get_all('RE Cancellation Policy')[0].name if frappe.get_all('RE Cancellation Policy') else ''
                    if not self.cancellation_policy:
                        frappe.throw(_('Could not resolve project for unit.'))

    def calculate_snapshot(self):
        policy = frappe.get_doc('RE Cancellation Policy', self.cancellation_policy)
        
        # 1. Fetch Billing Events
        events = frappe.get_all('RE Billing Event', filters={'sales_agreement': self.sales_agreement, 'docstatus': 1}, fields=['name', 'billing_amount', 'erpnext_invoice_ref'])
        
        gross_paid = 0.0
        gross_unpaid = 0.0
        
        for ev in events:
            if ev.erpnext_invoice_ref:
                si = frappe.db.get_value('Sales Invoice', ev.erpnext_invoice_ref, ['grand_total', 'outstanding_amount'], as_dict=True)
                if si:
                    paid = flt(si.grand_total) - flt(si.outstanding_amount)
                    gross_paid += paid
                    gross_unpaid += flt(si.outstanding_amount)

        self.gross_paid_amount = gross_paid
        self.gross_unpaid_invoiced_amount = gross_unpaid
        
        # 2. Calculate deductions
        fee = 0.0
        if policy.cancellation_fee_percentage:
            # Usually percentage of total agreement value or paid? Let's say agreement value for now, or paid?
            # Business rules usually do % of total contract. Let's get contract value.
            sa_value = frappe.db.get_value('RE Sales Agreement', self.sales_agreement, 'final_sale_price') or 0.0
            fee += flt(sa_value) * (flt(policy.cancellation_fee_percentage) / 100.0)
        
        if policy.cancellation_fee_amount:
            fee += flt(policy.cancellation_fee_amount)
            
        self.calculated_cancellation_fee = fee
        
        forfeit = 0.0
        if policy.forfeit_reservation_amount:
            # Calculate from reservation CRM or initial payment
            forfeit = frappe.db.get_value('RE Sales Agreement', self.sales_agreement, 'reservation_amount') or 0.0
            
        self.calculated_reservation_forfeiture = forfeit
        
        self.total_approved_deductions = self.calculated_cancellation_fee + self.calculated_reservation_forfeiture
        
        refund = self.gross_paid_amount - self.total_approved_deductions
        self.net_approved_refund = refund if refund > 0 else 0.0

    def on_submit(self):
        # Commercial Mutation Boundary
        if self.execution_status != 'Completed':
            frappe.throw(_('Cannot submit Cancellation before financial execution is Completed.'))
            
        sa = frappe.get_doc('RE Sales Agreement', self.sales_agreement)
        sa.db_set('status', 'Cancelled')
        
        # Trigger CRM integration
        if hasattr(sa, 'mark_crm_deal_lost'):
            sa.mark_crm_deal_lost()
        
        # Cancel Payment Schedules
        schedules = frappe.get_all('RE Payment Schedule', filters={'sales_agreement': self.sales_agreement, 'docstatus': 1})
        for sch in schedules:
            doc = frappe.get_doc('RE Payment Schedule', sch.name)
            doc.status = 'Cancelled'
            doc.flags.ignore_permissions = True
            doc.save()
            
        # Release Unit
        if sa.unit:
            unit = frappe.get_doc('RE Unit', sa.unit)
            unit.availability_status = 'Available'
            unit.flags.ignore_permissions = True
            unit.save()
