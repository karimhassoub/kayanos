# Copyright (c) 2026, Kayan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class REIntegrityFinding(Document):
    def validate(self):
        # finding_signature is normally set by the reconciliation engine,
        # but if created manually, we must not let it be empty.
        pass

    def on_trash(self):
        frappe.throw(_("RE Integrity Findings cannot be deleted. They must be resolved or marked as Accepted/Expected."))
