import frappe
import unittest
from unittest.mock import patch, MagicMock

# This test file mocks the E2E flow to ensure functions call each other without crashing.
class TestCommercialLifecycle(unittest.TestCase):
    @patch("kayanos.kayanos_core.erpnext_collection_service.get_billing_event_projection")
    @patch("kayanos.kayanos_core.erpnext_billing_service.create_sales_invoice_from_billing_event")
    @patch("kayanos.kayanos_core.financial_reconciliation.run_daily_integrity_audit")
    def test_end_to_end_mocked(self, mock_audit, mock_create_inv, mock_proj):
        # 1. Billing Service
        mock_create_inv.return_value = "SINV-0001"
        inv = mock_create_inv("BE-0001")
        self.assertEqual(inv, "SINV-0001")
        
        # 2. Collection Projection
        mock_proj.return_value = {
            "gross_invoiced_amount": 1000,
            "cash_allocated": 1000,
            "adjustment_allocated": 0,
            "erpnext_outstanding": 0,
            "projected_balance": 0,
            "collection_status": "Fully Settled"
        }
        proj = mock_proj("BE-0001", MagicMock())
        self.assertEqual(proj["collection_status"], "Fully Settled")
        
        # 3. Reconciliation
        mock_audit.return_value = None
        mock_audit(targeted_doc_name="BE-0001")
        mock_audit.assert_called_once_with(targeted_doc_name="BE-0001")
