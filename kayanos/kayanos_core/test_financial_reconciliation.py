import frappe
import unittest
from unittest.mock import patch, MagicMock
from kayanos.kayanos_core.financial_reconciliation import log_finding, run_daily_integrity_audit, get_finding_signature

class TestFinancialReconciliation(unittest.TestCase):
    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_log_finding_creates_new(self, mock_frappe):
        mock_frappe.db.get_value.return_value = None
        mock_doc = MagicMock()
        mock_frappe.new_doc.return_value = mock_doc
        
        active_sigs = set()
        log_finding("Missing Invoice", "Critical", "RE Billing Event", "BE-001", "Exists", "Missing", active_sigs)
        
        mock_frappe.new_doc.assert_called_with("RE Integrity Finding")
        mock_doc.insert.assert_called_once()
        self.assertEqual(len(active_sigs), 1)
        
    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_log_finding_reopens_resolved(self, mock_frappe):
        mock_frappe.db.get_value.return_value = "INT-001"
        mock_doc = MagicMock()
        mock_doc.status = "Resolved"
        mock_frappe.get_doc.return_value = mock_doc
        
        log_finding("Missing Invoice", "Critical", "RE Billing Event", "BE-001", "Exists", "Missing")
        
        self.assertEqual(mock_doc.status, "Open")
        mock_doc.save.assert_called_once()

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_detect_customer_mismatch(self, mock_frappe):
        # Mock Billing Event
        mock_be = MagicMock()
        mock_be.name = "BE-001"
        mock_be.erpnext_invoice_ref = "SINV-001"
        mock_be.customer = "Cust A"
        mock_be.currency = "USD"
        mock_be.get = lambda x: 100.0

        mock_frappe.get_all.side_effect = lambda doctype, **kwargs: [mock_be] if doctype == "RE Billing Event" else []
        mock_frappe.db.exists.return_value = True
        
        # Mock Invoice
        mock_inv = MagicMock()
        mock_inv.docstatus = 1
        mock_inv.customer = "Cust B"  # Mismatch!
        mock_inv.currency = "USD"
        mock_inv.items = []
        mock_frappe.get_doc.return_value = mock_inv
        
        with patch("kayanos.kayanos_core.financial_reconciliation.log_finding") as mock_log:
            with patch("kayanos.kayanos_core.financial_reconciliation.get_billing_event_projection", return_value={
                "gross_invoiced_amount": 100.0, "cash_allocated": 100.0, "adjustment_allocated": 100.0,
                "erpnext_outstanding": 100.0, "projected_balance": 100.0, "collection_status": "Paid"
            }):
                run_daily_integrity_audit(targeted_doc_name="BE-001")
                mock_log.assert_any_call("Customer Mismatch", "Critical", "RE Billing Event", "BE-001", "Cust A", "Cust B", mock_log.call_args[0][-1])

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_detect_unit_mismatch(self, mock_frappe):
        mock_be = MagicMock()
        mock_be.name = "BE-001"
        mock_be.erpnext_invoice_ref = "SINV-001"
        mock_be.customer = "Cust A"
        mock_be.currency = "USD"
        mock_be.unit = "UNIT-001"
        mock_be.get = lambda x: 100.0

        mock_frappe.get_all.side_effect = lambda doctype, **kwargs: [mock_be] if doctype == "RE Billing Event" else []
        mock_frappe.db.exists.return_value = True
        
        mock_inv = MagicMock()
        mock_inv.docstatus = 1
        mock_inv.customer = "Cust A"
        mock_inv.currency = "USD"
        row = MagicMock(); row.item_code = "WrongItem"
        mock_inv.items = [row]
        
        mock_unit = MagicMock(); mock_unit.shadow_item = "RealItem"
        
        def get_doc_side_effect(dt, name):
            if dt == "Sales Invoice": return mock_inv
            return None
            
        def get_cached_doc_side_effect(dt, name):
            if dt == "RE Unit": return mock_unit
            return None
            
        mock_frappe.get_doc.side_effect = get_doc_side_effect
        mock_frappe.get_cached_doc.side_effect = get_cached_doc_side_effect
        
        with patch("kayanos.kayanos_core.financial_reconciliation.log_finding") as mock_log:
            with patch("kayanos.kayanos_core.financial_reconciliation.get_billing_event_projection", return_value={
                "gross_invoiced_amount": 100.0, "cash_allocated": 100.0, "adjustment_allocated": 100.0,
                "erpnext_outstanding": 100.0, "projected_balance": 100.0, "collection_status": "Paid"
            }):
                run_daily_integrity_audit(targeted_doc_name="BE-001")
                mock_log.assert_any_call("Unit Mismatch", "Critical", "RE Billing Event", "BE-001", "RealItem", "WrongItem", mock_log.call_args[0][-1])

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_detect_schedule_orphans(self, mock_frappe):
        mock_frappe.get_all.return_value = []
        mock_frappe.db.sql.return_value = [{"name": "SCH-001", "installment_amount": 1000.0, "due_date": "2020-01-01"}]
        mock_frappe.utils.nowdate.return_value = "2026-01-01"
        
        with patch("kayanos.kayanos_core.financial_reconciliation.log_finding") as mock_log:
            run_daily_integrity_audit()
            mock_log.assert_any_call("Orphan Payment Schedule", "Warning", "RE Payment Schedule", "SCH-001", "Has Billing Event", "Missing", mock_log.call_args[0][-1])

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_detect_invoice_orphans(self, mock_frappe):
        def get_all_side_effect(dt, **kwargs):
            if dt == "RE Unit": return ["Item-Unit"]
            if dt == "Sales Invoice Item": return ["SINV-Orphan"]
            if dt == "RE Integrity Finding": return []
            return []
            
        mock_frappe.get_all.side_effect = get_all_side_effect
        mock_frappe.db.count.return_value = 0 # No billing event
        mock_frappe.db.sql.return_value = []
        
        with patch("kayanos.kayanos_core.financial_reconciliation.log_finding") as mock_log:
            run_daily_integrity_audit()
            mock_log.assert_any_call("Orphan Invoice", "Critical", "Sales Invoice", "SINV-Orphan", "Has Billing Event", "Missing", mock_log.call_args[0][-1])

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_scoped_auto_resolution(self, mock_frappe):
        # Mock findings
        mock_frappe.get_all.side_effect = lambda dt, **kwargs: [{"name": "INT-001", "finding_signature": "sig1"}] if dt == "RE Integrity Finding" else []
        mock_frappe.db.sql.return_value = []
        
        # We target BE-001. active_signatures is empty for this run.
        # Since targeted_doc_name is BE-001, the finding will be fetched and resolved.
        run_daily_integrity_audit(targeted_doc_name="BE-001")
        mock_frappe.db.set_value.assert_called_with("RE Integrity Finding", "INT-001", "status", "Resolved")

    @patch("kayanos.kayanos_core.financial_reconciliation.frappe")
    def test_batch_failure_isolation(self, mock_frappe):
        mock_be1 = MagicMock(); mock_be1.name = "BE-001"; mock_be1.erpnext_invoice_ref = "SINV-001"
        mock_be2 = MagicMock(); mock_be2.name = "BE-002"; mock_be2.erpnext_invoice_ref = "SINV-002"
        
        def get_all_side_effect(dt, **kwargs):
            if dt == "RE Billing Event": return [mock_be1, mock_be2]
            return []
            
        mock_frappe.get_all.side_effect = get_all_side_effect
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.sql.return_value = []
        
        with patch("kayanos.kayanos_core.financial_reconciliation.get_billing_event_projection") as mock_proj:
            # First fails, second succeeds
            good_proj = {
                "gross_invoiced_amount": 100.0, "cash_allocated": 100.0, "adjustment_allocated": 100.0,
                "erpnext_outstanding": 100.0, "projected_balance": 100.0, "collection_status": "Paid"
            }
            mock_proj.side_effect = [Exception("Test"), good_proj]
            
            run_daily_integrity_audit()
            
            # Ensure log_error was called for the first
            mock_frappe.log_error.assert_called_with("Reconciliation Projection Error", "Test")
            # Ensure it continued to process the second event
            self.assertEqual(mock_proj.call_count, 2)
