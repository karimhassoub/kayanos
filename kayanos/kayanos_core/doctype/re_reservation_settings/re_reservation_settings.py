import frappe
from frappe.model.document import Document
from frappe import _

class REReservationSettings(Document):
    def validate(self):
        if self.default_reservation_duration_hours <= 0:
            frappe.throw(_("Default Reservation Duration must be greater than zero."))
