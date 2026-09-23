import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_to_date
from frappe import _

class REUnitReservation(Document):
    def validate(self):
        self.enforce_immutability()
        self.sync_crm_data()
        self.validate_state_transitions()
        self.handle_transitions()

    def enforce_immutability(self):
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc:
                if old_doc.crm_deal and self.crm_deal != old_doc.crm_deal:
                    frappe.throw(_("Cannot change CRM Deal after creation."))
                if old_doc.unit and self.unit != old_doc.unit:
                    frappe.throw(_("Cannot change Unit after creation."))

    def sync_crm_data(self):
        if self.crm_deal:
            lead, org = frappe.db.get_value("CRM Deal", self.crm_deal, ["lead", "organization"])
            self.lead = lead
            self.organization = org

    def validate_state_transitions(self):
        if self.is_new():
            if self.status not in ["Draft", "Active"]:
                frappe.throw(_("New reservation must be Draft or Active."))
        else:
            old_status = self.get_doc_before_save().status if self.get_doc_before_save() else "Draft"
            if old_status != self.status:
                valid_transitions = {
                    "Draft": ["Active"],
                    "Active": ["Cancelled", "Expired", "Converted"],
                    "Cancelled": [],
                    "Expired": [],
                    "Converted": []
                }
                if self.status not in valid_transitions.get(old_status, []):
                    frappe.throw(_("Invalid state transition from {0} to {1}").format(old_status, self.status))

    def handle_transitions(self):
        old_status = self.get_doc_before_save().status if not self.is_new() and self.get_doc_before_save() else "Draft"
        
        if self.status == "Active" and old_status != "Active":
            self.activate_reservation()
        elif self.status in ["Cancelled", "Expired"] and old_status == "Active":
            self.deactivate_reservation()

    def activate_reservation(self):
        # 1. Lock Unit
        unit_status = frappe.db.get_value("RE Unit", self.unit, "availability_status", for_update=True)
        
        if unit_status != "Available":
            frappe.throw(_("Unit is not Available. Current status: {0}").format(unit_status))
            
        unit_doc = frappe.get_doc("RE Unit", self.unit)
        if unit_doc.lifecycle_status != "Active":
            frappe.throw(_("Unit lifecycle is not Active."))
            
        # 2. Phase & Project sales auth validation
        phase_name = frappe.db.get_value("RE Property", unit_doc.property, "phase")
        project_name = frappe.db.get_value("RE Phase", phase_name, "project")
        
        phase_sales = frappe.db.get_value("RE Phase", phase_name, "sales_authorized")
        if not phase_sales:
            frappe.throw(_("Phase sales authorization is not active."))
            
        profile_sales = frappe.db.get_value("RE Project Profile", {"project": project_name}, "sales_authorized")
        if profile_sales == 0:
            frappe.throw(_("Project sales authorization is not active."))

        # 3. Uniqueness checks inside lock
        existing_unit_res = frappe.db.exists("RE Unit Reservation", {"unit": self.unit, "status": "Active", "name": ("!=", self.name)})
        if existing_unit_res:
            frappe.throw(_("Unit already has an Active reservation."))

        existing_deal_res = frappe.db.exists("RE Unit Reservation", {"crm_deal": self.crm_deal, "status": "Active", "name": ("!=", self.name)})
        if existing_deal_res:
            frappe.throw(_("CRM Deal already has an Active reservation."))

        # 4. Set expiry
        duration = frappe.db.get_single_value("RE Reservation Settings", "default_reservation_duration_hours") or 48.0
        if duration <= 0:
            frappe.throw(_("Reservation duration must be greater than 0."))
        self.expiry_time = add_to_date(now_datetime(), hours=float(duration))
        
        # 5. Update Unit Status
        frappe.db.set_value("RE Unit", self.unit, "availability_status", "Reserved")
        
        # 6. Queue Email Notification (Model A)
        frappe.enqueue(
            "kayanos.kayanos_core.notifications.send_reservation_confirmation",
            reservation_name=self.name,
            enqueue_after_commit=True
        )

    def deactivate_reservation(self):
        # 1. Lock Unit
        frappe.db.get_value("RE Unit", self.unit, "availability_status", for_update=True)
        
        # 2. Check if there are OTHER active reservations? (Self is not saved yet, so DB might say Self is Active, but we exclude it)
        other_active = frappe.db.exists("RE Unit Reservation", {"unit": self.unit, "status": "Active", "name": ("!=", self.name)})
        
        if not other_active:
            frappe.db.set_value("RE Unit", self.unit, "availability_status", "Available")


def expire_reservations():
    expired = frappe.get_all("RE Unit Reservation", filters={"status": "Active", "expiry_time": ("<=", now_datetime())}, pluck="name")
    for res_name in expired:
        try:
            # Lock the row to prevent race conditions with conversion
            status = frappe.db.get_value("RE Unit Reservation", res_name, "status", for_update=True)
            if status != "Active":
                continue
                
            res = frappe.get_doc("RE Unit Reservation", res_name)
            # Re-check expiry time
            if res.expiry_time > now_datetime():
                continue
                
            res.status = "Expired"
            res.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title="Failed to expire reservation", message=str(e))


def convert_reservation(reservation_name):
    """
    Server-side transactional operation to convert an Active reservation.
    Prepares the reservation for the future Sales Agreement.
    """
    if not reservation_name:
        frappe.throw(_("Reservation name is required"))
        
    # Lock reservation
    status = frappe.db.get_value("RE Unit Reservation", reservation_name, "status", for_update=True)
    if not status:
        frappe.throw(_("Reservation {0} not found").format(reservation_name))
        
    if status == "Converted":
        frappe.throw(_("Reservation {0} is already converted").format(reservation_name))
    
    if status != "Active":
        frappe.throw(_("Only Active reservations can be converted. Current status: {0}").format(status))
        
    res = frappe.get_doc("RE Unit Reservation", reservation_name)
    
    if res.expiry_time and res.expiry_time <= now_datetime():
        frappe.throw(_("Cannot convert an expired reservation."))
        
    # Lock unit
    unit_status = frappe.db.get_value("RE Unit", res.unit, "availability_status", for_update=True)
    if not unit_status:
        frappe.throw(_("Unit not found"))
        
    if unit_status != "Reserved":
        frappe.throw(_("Unit must be Reserved to convert reservation. Current status: {0}").format(unit_status))
        
    # Check for competing active reservation
    competing = frappe.db.exists("RE Unit Reservation", {"unit": res.unit, "status": "Active", "name": ("!=", reservation_name)})
    if competing:
        frappe.throw(_("A competing active reservation exists for this unit."))
        
    if not res.crm_deal:
        frappe.throw(_("Reservation must have a valid CRM Deal to be converted."))
        
    res.status = "Converted"
    res.save(ignore_permissions=True)
    
    return res.name

