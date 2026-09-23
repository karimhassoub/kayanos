import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

from kayanos.kayanos_core.doctype.re_payment_plan_installment.re_payment_plan_installment import validate_payment_plan
from kayanos.kayanos_core.customer_bridge import get_or_create_customer

class RESalesAgreement(Document):
    def validate(self):
        self.set_commercial_snapshot()
        self.ensure_customer_linked()
        self.validate_and_calculate_payment_plan()
        self.validate_state_transitions()
        
    def set_commercial_snapshot(self):
        self.unit_price = flt(self.unit_price)
        self.discount = flt(self.discount)
        self.final_sale_price = self.unit_price - self.discount
        
        if self.final_sale_price <= 0:
            frappe.throw(_("Final Sale Price must be strictly greater than zero."))
            
    def ensure_customer_linked(self):
        if not self.customer and self.crm_deal:
            self.customer = get_or_create_customer(self.crm_deal)
            
    def validate_and_calculate_payment_plan(self):
        if self.payment_plan:
            validate_payment_plan(self.payment_plan, self.final_sale_price)

    def validate_state_transitions(self):
        if self.is_new():
            if self.status != "Draft":
                frappe.throw(_("New Agreement must be created as Draft."))
            self.validate_draft_creation()
        else:
            old_status = self.get_doc_before_save().status
            if old_status != self.status:
                frappe.throw(_("Status cannot be changed directly via save. Use appropriate lifecycle methods."))

    def validate_draft_creation(self):
        res_status = frappe.db.get_value("RE Unit Reservation", self.reservation, "status")
        if res_status != "Active":
            frappe.throw(_("Reservation must be Active to create a Draft Agreement."))
            
        duplicate = frappe.db.exists("RE Sales Agreement", {"reservation": self.reservation, "status": ["in", ["Draft", "Confirmed"]], "name": ("!=", self.name)})
        if duplicate:
            frappe.throw(_("An active or draft Agreement already exists for this reservation."))

    @frappe.whitelist()
    def confirm_agreement(self):
        roles = frappe.get_roles(frappe.session.user)
        if "Sales Manager" not in roles and "System Manager" not in roles:
            raise frappe.PermissionError(_("Only Sales Manager or System Manager can confirm an Agreement."))
            
        frappe.db.get_value("RE Unit Reservation", self.reservation, "name", for_update=True)
        frappe.db.get_value("RE Unit", self.unit, "name", for_update=True)
        
        self.reload()
        
        if self.status != "Draft":
            frappe.throw(_("Agreement is not in Draft state."))
            
        res = frappe.get_doc("RE Unit Reservation", self.reservation)
        if res.status != "Active":
            frappe.throw(_("Reservation is no longer Active."))
            
        if res.expiry_time and res.expiry_time <= frappe.utils.now_datetime():
            frappe.throw(_("Reservation has expired."))
            
        unit = frappe.get_doc("RE Unit", self.unit)
        if unit.availability_status != "Reserved":
            frappe.throw(_("Unit is no longer Reserved."))
            
        phase_name = frappe.db.get_value("RE Property", unit.property, "phase")
        project_name = frappe.db.get_value("RE Phase", phase_name, "project")
        
        if not frappe.db.get_value("RE Phase", phase_name, "sales_authorized"):
            frappe.throw(_("Phase sales authorization is not active."))
        if not frappe.db.get_value("RE Project Profile", {"project": project_name}, "sales_authorized"):
            frappe.throw(_("Project sales authorization is not active."))
            
        if not self.payment_plan:
            frappe.throw(_("Payment plan is required."))
        validate_payment_plan(self.payment_plan, self.final_sale_price)
        
        other_confirmed = frappe.db.exists("RE Sales Agreement", {"unit": self.unit, "status": "Confirmed", "name": ("!=", self.name)})
        if other_confirmed:
            frappe.throw(_("Another Confirmed Agreement already exists for this unit."))
            
        self.db_set("status", "Confirmed")
        
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        convert_reservation(self.reservation)
        
        unit.availability_status = "Sold"
        unit.save(ignore_permissions=True)
        
        self.generate_payment_schedule()
        
        # Queue Email Notification (Model A)
        frappe.enqueue(
            "kayanos.kayanos_core.notifications.send_agreement_confirmation",
            agreement_name=self.name,
            enqueue_after_commit=True
        )

    @frappe.whitelist()
    def cancel_draft_agreement(self):
        roles = frappe.get_roles(frappe.session.user)
        if "Sales Manager" not in roles and "System Manager" not in roles:
            raise frappe.PermissionError(_("Only Sales Manager or System Manager can cancel an Agreement."))
            
        self.reload()
        if self.status != "Draft":
            frappe.throw(_("Only Draft agreements can be cancelled using this method."))
            
        self.db_set("status", "Cancelled")

    @frappe.whitelist()
    def cancel_confirmed_agreement(self):
        roles = frappe.get_roles(frappe.session.user)
        if "Sales Manager" not in roles and "System Manager" not in roles:
            raise frappe.PermissionError(_("Only Sales Manager or System Manager can cancel an Agreement."))

            
        frappe.db.get_value("RE Unit Reservation", self.reservation, "name", for_update=True)
        frappe.db.get_value("RE Unit", self.unit, "name", for_update=True)
        
        self.reload()
        if self.status != "Confirmed":
            frappe.throw(_("Only Confirmed agreements can be cancelled using this method."))
            
        self.db_set("status", "Cancelled")
        
        other_confirmed = frappe.db.exists("RE Sales Agreement", {"unit": self.unit, "status": "Confirmed", "name": ("!=", self.name)})
        other_reserved = frappe.db.exists("RE Unit Reservation", {"unit": self.unit, "status": "Active"})
        
        if not other_confirmed and not other_reserved:
            unit = frappe.get_doc("RE Unit", self.unit)
            phase_name = frappe.db.get_value("RE Property", unit.property, "phase")
            project_name = frappe.db.get_value("RE Phase", phase_name, "project")
            
            phase_auth = frappe.db.get_value("RE Phase", phase_name, "sales_authorized")
            proj_auth = frappe.db.get_value("RE Project Profile", {"project": project_name}, "sales_authorized")
            
            if phase_auth and proj_auth:
                unit.availability_status = "Available"
            else:
                unit.availability_status = "Withheld"
            unit.save(ignore_permissions=True)
            
        self.mark_crm_deal_lost()
        self.cancel_payment_schedule()
        
    def generate_payment_schedule(self):
        if self.status != "Confirmed":
            frappe.throw(_("Cannot generate payment schedule for an unconfirmed agreement."))
            
        existing = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": self.name, "status": ("!=", "Cancelled")})
        if existing:
            if len(existing) != len(self.payment_plan):
                frappe.throw(_("Payment schedule is partially generated or inconsistent. Manual intervention required."))
            return
            
        if not self.payment_plan:
            frappe.throw(_("Cannot generate payment schedule: Payment plan is missing."))
            
        seq = 1
        for row in self.payment_plan:
            schedule = frappe.new_doc("RE Payment Schedule")
            schedule.sales_agreement = self.name
            schedule.installment_sequence = seq
            schedule.installment_type = row.installment_type
            schedule.due_date = row.due_date
            schedule.payment_percentage = row.percentage
            schedule.installment_amount = row.amount
            schedule.currency = self.currency
            schedule.status = "Pending"
            
            schedule.flags.ignore_permissions = True
            schedule.insert(ignore_permissions=True)
            seq += 1

    def cancel_payment_schedule(self):
        schedules = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": self.name, "status": "Pending"}, pluck="name")
        for sch_name in schedules:
            sch = frappe.get_doc("RE Payment Schedule", sch_name)
            sch.status = "Cancelled"
            sch.flags.ignore_permissions = True
            sch.save(ignore_permissions=True)
            
        # Flag Invoiced Billing Events for Financial Review
        all_schedules = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": self.name}, pluck="name")
        if all_schedules:
            invoiced_events = frappe.get_all(
                "RE Billing Event", 
                filters={
                    "payment_schedule": ["in", all_schedules],
                    "status": "Invoiced",
                    "financial_review_status": ["!=", "Resolved"]
                }, 
                pluck="name"
            )
            for event_name in invoiced_events:
                frappe.db.set_value("RE Billing Event", event_name, "financial_review_status", "Pending Review")
            
    def mark_crm_deal_lost(self):
        if not self.crm_deal:
            return
            
        if not frappe.db.exists("CRM Deal", self.crm_deal):
            return
            
        deal = frappe.get_doc("CRM Deal", self.crm_deal)
        
        lost_type_status = frappe.db.get_value("CRM Deal Status", {"type": "Lost"}, "name")
        if not lost_type_status:
            frappe.throw(_("Cannot mark CRM Deal as Lost: No CRM Deal Status of type 'Lost' found in the system."))
            
        if deal.status == lost_type_status:
            return
            
        current_type = frappe.db.get_value("CRM Deal Status", deal.status, "type")
        if current_type == "Won":
            frappe.throw(_("Cannot mark CRM Deal as Lost: Deal is already Won."))
            
        deal.status = lost_type_status
        
        lost_reason = frappe.db.get_value("CRM Lost Reason", {"name": ["like", "%Cancel%"]}, "name")
        if not lost_reason:
            lost_reason = frappe.db.get_value("CRM Lost Reason", None, "name")
            
        if not lost_reason:
            frappe.throw(_("Cannot mark CRM Deal as Lost: No 'CRM Lost Reason' exists in the system. Please create one."))
            
        deal.lost_reason = lost_reason
        deal.lost_notes = "Automatically marked as lost due to Sales Agreement Cancellation."
        
        try:
            deal.save(ignore_permissions=True)
        except frappe.ValidationError as e:
            frappe.throw(_("Failed to mark CRM Deal as Lost due to CRM validation: {0}").format(str(e)))
