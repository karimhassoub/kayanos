import frappe
import unittest
from unittest.mock import patch, MagicMock
from kayanos.kayanos_core.erpnext_collection_service import sync_collections_for_invoice, _process_billing_event_sync

class TestERPNextCollectionsUnit(unittest.TestCase):
    def setUp(self):
        # Create a real RE Billing Event so we can test the actual update logic
        # We don't need a real Sales Agreement for the isolated test, we can just mock the properties
        self.event_name = "MOCK-EVENT-001"
        self.invoice_name = "MOCK-SI-001"
        
        # We'll use a mocked event object that intercepts db_set
        self.mock_event = MagicMock()
        self.mock_event.name = self.event_name
        self.mock_event.currency = "EGP"
        self.mock_event.returned_amount = 0.0
        
        self.mock_invoice = MagicMock()
        self.mock_invoice.name = self.invoice_name
        self.mock_invoice.currency = "EGP"
        self.mock_invoice.grand_total = 1000.0
        self.mock_invoice.outstanding_amount = 1000.0
        self.mock_invoice.precision.return_value = 2

    @patch('kayanos.kayanos_core.erpnext_collection_service.frappe')
    def test_01_unpaid_status(self, mock_frappe):
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_doc.return_value = self.mock_event
        mock_frappe.get_all.return_value = [] # No PEs or JEs
        
        _process_billing_event_sync(self.event_name, self.mock_invoice)
        
        self.mock_event.db_set.assert_any_call("collection_status", "Unpaid", update_modified=True)
        self.mock_event.db_set.assert_any_call("cash_allocated", 0.0, update_modified=True)
        self.mock_event.db_set.assert_any_call("projected_balance", 1000.0, update_modified=True)

    @patch('kayanos.kayanos_core.erpnext_collection_service.frappe')
    def test_02_partial_cash_allocation(self, mock_frappe):
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_doc.return_value = self.mock_event
        
        def mock_get_all(doctype, **kwargs):
            if doctype == "Payment Entry Reference":
                mock_ref = MagicMock()
                mock_ref.allocated_amount = 500.0
                return [mock_ref]
            return []
        mock_frappe.get_all.side_effect = mock_get_all
        
        self.mock_invoice.outstanding_amount = 500.0 # Partially paid
        _process_billing_event_sync(self.event_name, self.mock_invoice)
        
        self.mock_event.db_set.assert_any_call("collection_status", "Partially Settled", update_modified=True)
        self.mock_event.db_set.assert_any_call("cash_allocated", 500.0, update_modified=True)
        self.mock_event.db_set.assert_any_call("projected_balance", 500.0, update_modified=True)

    @patch('kayanos.kayanos_core.erpnext_collection_service.frappe')
    def test_03_full_settlement(self, mock_frappe):
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_doc.return_value = self.mock_event
        
        def mock_get_all(doctype, **kwargs):
            if doctype == "Payment Entry Reference":
                mock_ref = MagicMock()
                mock_ref.allocated_amount = 1000.0
                return [mock_ref]
            return []
        mock_frappe.get_all.side_effect = mock_get_all
        
        self.mock_invoice.outstanding_amount = 0.0
        _process_billing_event_sync(self.event_name, self.mock_invoice)
        
        self.mock_event.db_set.assert_any_call("collection_status", "Fully Settled", update_modified=True)
        self.mock_event.db_set.assert_any_call("cash_allocated", 1000.0, update_modified=True)
        self.mock_event.db_set.assert_any_call("projected_balance", 0.0, update_modified=True)

    @patch('kayanos.kayanos_core.erpnext_collection_service.frappe')
    def test_04_je_adjustment_allocation(self, mock_frappe):
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_doc.return_value = self.mock_event
        
        def mock_get_all(doctype, **kwargs):
            if doctype == "Journal Entry Account":
                mock_ref = MagicMock()
                mock_ref.credit_in_account_currency = 300.0
                mock_ref.parent = "JE-001"
                return [mock_ref]
            return []
        mock_frappe.get_all.side_effect = mock_get_all
        
        self.mock_invoice.outstanding_amount = 700.0
        _process_billing_event_sync(self.event_name, self.mock_invoice)
        
        self.mock_event.db_set.assert_any_call("collection_status", "Partially Settled", update_modified=True)
        self.mock_event.db_set.assert_any_call("cash_allocated", 0.0, update_modified=True)
        self.mock_event.db_set.assert_any_call("adjustment_allocated", 300.0, update_modified=True)
        self.mock_event.db_set.assert_any_call("projected_balance", 700.0, update_modified=True)

    @patch('kayanos.kayanos_core.erpnext_collection_service.frappe')
    def test_05_returns_processing(self, mock_frappe):
        self.mock_event.returned_amount = 1000.0
        
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_doc.return_value = self.mock_event
        mock_frappe.get_all.return_value = []
        
        self.mock_invoice.outstanding_amount = 0.0
        _process_billing_event_sync(self.event_name, self.mock_invoice)
        
        self.mock_event.db_set.assert_any_call("collection_status", "Fully Returned", update_modified=True)
        self.mock_event.db_set.assert_any_call("projected_balance", 0.0, update_modified=True)
