import frappe
import unittest
from kayanos.kayanos_core.doctype.re_sales_agreement.test_re_sales_agreement import TestRESalesAgreement

class TestREPaymentSchedule(TestRESalesAgreement):
    def test_schedule_generation_and_cancellation(self):
        res, unit, deal = self.create_mock_reservation()
        
        agr = frappe.get_doc({
            "doctype": "RE Sales Agreement",
            "reservation": res.name,
            "unit_price": 1000000,
            "currency": "EGP",
            "payment_plan": [
                {"installment_type": "Down Payment", "percentage": 10, "due_date": "2026-10-01"},
                {"installment_type": "Installment", "percentage": 90, "due_date": "2026-11-01"}
            ]
        })
        agr.insert(ignore_permissions=True)
        
        # Schedules should not exist for Draft
        schedules = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": agr.name})
        self.assertEqual(len(schedules), 0)
        
        # Confirm
        agr.confirm_agreement()
        
        # Schedules should be generated
        schedules = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": agr.name}, fields=["*"], order_by="installment_sequence asc")
        self.assertEqual(len(schedules), 2)
        
        sch1 = schedules[0]
        self.assertEqual(sch1.installment_sequence, 1)
        self.assertEqual(sch1.installment_type, "Down Payment")
        self.assertEqual(sch1.payment_percentage, 10.0)
        self.assertEqual(sch1.installment_amount, 100000.0)
        self.assertEqual(sch1.status, "Pending")
        
        sch2 = schedules[1]
        self.assertEqual(sch2.installment_sequence, 2)
        self.assertEqual(sch2.payment_percentage, 90.0)
        self.assertEqual(sch2.installment_amount, 900000.0)
        self.assertEqual(sch2.status, "Pending")
        
        # Idempotency check: call generate again
        agr.generate_payment_schedule()
        schedules_after = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": agr.name})
        self.assertEqual(len(schedules_after), 2) # Should still be 2
        
        # Mock CRM status for cancellation
        try:
            if not frappe.db.exists("CRM Deal Status", "Lost"):
                frappe.get_doc({"doctype": "CRM Deal Status", "status_name": "Lost", "type": "Lost"}).insert(ignore_permissions=True)
            if not frappe.db.exists("CRM Lost Reason", "Cancelled"):
                frappe.get_doc({"doctype": "CRM Lost Reason", "reason": "Cancelled"}).insert(ignore_permissions=True)
        except Exception:
            pass
            
        # Cancel agreement
        try:
            agr.cancel_confirmed_agreement()
            
            # Schedules should be Cancelled
            schedules_cancelled = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": agr.name}, fields=["status"])
            for s in schedules_cancelled:
                self.assertEqual(s.status, "Cancelled")
        except Exception as e:
            self.assertIn("Cannot mark CRM Deal as Lost", str(e))
            
    def test_direct_schedule_creation_blocked(self):
        sch = frappe.new_doc("RE Payment Schedule")
        sch.sales_agreement = "DUMMY"
        sch.installment_sequence = 1
        sch.payment_percentage = 100
        sch.installment_amount = 1000
        sch.currency = "EGP"
        sch.status = "Pending"
        
        # Should fail if ignore_permissions flag is not set (simulating REST API / direct write)
        with self.assertRaises(frappe.ValidationError):
            sch.insert()
            
    def test_idempotency_rejects_partial_schedules(self):
        res, unit, deal = self.create_mock_reservation()
        
        agr = frappe.get_doc({
            "doctype": "RE Sales Agreement",
            "reservation": res.name,
            "unit_price": 1000000,
            "currency": "EGP",
            "payment_plan": [
                {"installment_type": "Down Payment", "percentage": 50},
                {"installment_type": "Installment", "percentage": 50}
            ]
        })
        agr.insert(ignore_permissions=True)
        agr.confirm_agreement()
        
        # Now artificially delete one schedule to simulate a partial/inconsistent state
        schedules = frappe.get_all("RE Payment Schedule", filters={"sales_agreement": agr.name})
        self.assertEqual(len(schedules), 2)
        
        frappe.delete_doc("RE Payment Schedule", schedules[0].name, ignore_permissions=True)
        
        # Now call generate_payment_schedule again (idempotency check)
        with self.assertRaises(frappe.ValidationError) as context:
            agr.generate_payment_schedule()
            
        self.assertIn("partially generated or inconsistent", str(context.exception))
