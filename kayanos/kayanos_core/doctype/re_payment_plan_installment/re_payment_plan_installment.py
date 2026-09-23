import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt

class REPaymentPlanInstallment(Document):
    def validate(self):
        if self.amount < 0:
            frappe.throw(_("Installment amount cannot be negative."))
        if self.percentage and self.percentage < 0:
            frappe.throw(_("Installment percentage cannot be negative."))

def validate_payment_plan(installments, total_amount):
    """
    Validates a list of RE Payment Plan Installment dictionaries or documents
    against a given total amount. Calculates the amount from percentage to
    prevent tampering and ensure the percentage is the source of truth.
    """
    if not installments:
        frappe.throw(_("Payment plan must have at least one installment."))
        
    total_amount = flt(total_amount, 2)
    if total_amount <= 0:
        frappe.throw(_("Total amount must be greater than zero."))
        
    sum_percentage = 0.0
    
    for row in installments:
        percentage = flt(row.get("percentage"), 6)
        if percentage <= 0:
            frappe.throw(_("Installment percentage must be strictly greater than zero."))
        sum_percentage += percentage

    if abs(sum_percentage - 100.0) > 0.001:
        frappe.throw(_("Total installments percentage ({0}%) must equal exactly 100%.").format(sum_percentage))
        
    # Calculate amounts and distribute rounding difference to the last installment
    # Business Rule: Fractional penny differences resulting from percentage calculations
    # must be allocated exclusively to the final installment to guarantee the total
    # installment amount matches the final sale price exactly.
    calculated_sum = 0.0
    for i, row in enumerate(installments):
        percentage = flt(row.get("percentage"), 2)
        amount = flt((percentage / 100.0) * total_amount, 2)
        
        # If this is the last installment, absorb any rounding difference
        if i == len(installments) - 1:
            amount = flt(total_amount - calculated_sum, 2)
            
        if hasattr(row, "amount"):
            row.amount = amount
        else:
            row["amount"] = amount
            
        calculated_sum += amount
