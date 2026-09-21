import frappe
from frappe.model.document import Document
from frappe import _

class REPaymentSchedule(Document):
    def validate(self):
        if not self.flags.ignore_permissions and not frappe.flags.in_test:
            frappe.throw(_("Payment Schedule records can only be generated or modified by the system."))
