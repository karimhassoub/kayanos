import frappe
import unittest
from kayanos.kayanos_core.doctype.re_payment_plan_installment.re_payment_plan_installment import validate_payment_plan

class TestREPaymentPlanInstallment(unittest.TestCase):
    def test_01_valid_plan_calculates_amount(self):
        installments = [
            {"installment_type": "Down Payment", "percentage": 10},
            {"installment_type": "Installment", "percentage": 90}
        ]
        validate_payment_plan(installments, 1000000)
        self.assertEqual(installments[0]["amount"], 100000.0)
        self.assertEqual(installments[1]["amount"], 900000.0)

    def test_02_empty_plan(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_payment_plan([], 1000000)

    def test_03_zero_total_amount(self):
        installments = [
            {"installment_type": "Down Payment", "percentage": 100}
        ]
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_payment_plan(installments, 0)

    def test_04_negative_or_zero_percentage(self):
        installments = [
            {"installment_type": "Down Payment", "percentage": -10},
            {"installment_type": "Installment", "percentage": 110}
        ]
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_payment_plan(installments, 1000000)
            
        installments_zero = [
            {"installment_type": "Down Payment", "percentage": 0},
            {"installment_type": "Installment", "percentage": 100}
        ]
        with self.assertRaises(frappe.exceptions.ValidationError):
            validate_payment_plan(installments_zero, 1000000)

    def test_05_amount_tampering_is_overwritten(self):
        installments = [
            # User tries to tamper with the amount manually
            {"installment_type": "Down Payment", "percentage": 10, "amount": 500000},
            {"installment_type": "Installment", "percentage": 90, "amount": 500000}
        ]
        validate_payment_plan(installments, 1000000)
        # Server must override tampered amounts based on percentage
        self.assertEqual(installments[0]["amount"], 100000.0)
        self.assertEqual(installments[1]["amount"], 900000.0)

    def test_06_total_percentage_mismatch(self):
        installments = [
            {"installment_type": "Down Payment", "percentage": 50},
            {"installment_type": "Installment", "percentage": 49.99} # forces percentage sum to 99.99
        ]
        with self.assertRaises(frappe.exceptions.ValidationError) as context:
            validate_payment_plan(installments, 1000000)
        self.assertIn("must equal exactly 100%", str(context.exception))

    def test_07_fractional_rounding_tolerance_and_distribution(self):
        installments = [
            {"installment_type": "Installment", "percentage": 33.33},
            {"installment_type": "Installment", "percentage": 33.33},
            {"installment_type": "Installment", "percentage": 33.34} # total is 100.00
        ]
        validate_payment_plan(installments, 1000000)
        # Expected amounts: 333300, 333300, 333400
        self.assertEqual(installments[0]["amount"], 333300.0)
        self.assertEqual(installments[1]["amount"], 333300.0)
        self.assertEqual(installments[2]["amount"], 333400.0)
        
    def test_08_fractional_penny_distribution(self):
        installments = [
            {"installment_type": "Installment", "percentage": 33.333333},
            {"installment_type": "Installment", "percentage": 33.333333},
            {"installment_type": "Installment", "percentage": 33.333334} # rounds to 33.33, 33.33, 33.34
        ]
        validate_payment_plan(installments, 100) # 100 total
        # Expected amounts: 33.33, 33.33, 33.34
        self.assertEqual(installments[0]["amount"], 33.33)
        self.assertEqual(installments[1]["amount"], 33.33)
        self.assertEqual(installments[2]["amount"], 33.34)
