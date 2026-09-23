import frappe
import unittest
from unittest.mock import patch, MagicMock
from kayanos.kayanos_core.collection_automation import send_collection_reminders

class TestCollectionAutomation(unittest.TestCase):
    @patch("kayanos.kayanos_core.collection_automation.frappe")
    def test_send_reminders_creates_communication(self, mock_frappe):
        mock_be = MagicMock()
        mock_be.name = "BE-TEST"
        mock_be.customer = "Cust A"
        mock_be.sales_agreement = "SA-001"
        mock_be.projected_balance = 5000
        mock_be.due_date = "2026-01-01"
        
        # Mock overdue events
        mock_frappe.db.sql.return_value = [
            {"name": "BE-TEST", "customer": "Cust A", "sales_agreement": "SA-001", "projected_balance": 5000, "due_date": "2026-01-01"}
        ]
        
        # Mock communication does NOT exist (no reminder sent today)
        mock_frappe.db.exists.return_value = False
        
        # Mock Customer
        mock_customer = MagicMock()
        mock_customer.email_id = "test@example.com"
        mock_frappe.get_cached_doc.return_value = mock_customer
        
        mock_doc = MagicMock()
        mock_frappe.get_doc.return_value = mock_doc
        
        send_collection_reminders()
        
        # Assert communication created
        mock_frappe.get_doc.assert_called_once()
        mock_doc.insert.assert_called_once()
        
    @patch("kayanos.kayanos_core.collection_automation.frappe")
    def test_send_reminders_prevents_duplicate(self, mock_frappe):
        # Mock overdue events
        mock_frappe.db.sql.return_value = [
            {"name": "BE-TEST", "customer": "Cust A", "sales_agreement": "SA-001", "projected_balance": 5000, "due_date": "2026-01-01"}
        ]
        
        # Mock communication DOES exist (already sent today)
        mock_frappe.db.exists.return_value = True
        
        send_collection_reminders()
        
        # Assert no communication is created
        mock_frappe.get_doc.assert_not_called()
