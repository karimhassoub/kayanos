import frappe
import unittest
from unittest.mock import patch, MagicMock
from kayanos.kayanos_core.report.re_customer_commercial_statement.re_customer_commercial_statement import get_data as get_customer_statement_data
from kayanos.kayanos_core.report.re_commercial_collection_summary.re_commercial_collection_summary import get_data as get_collection_summary_data
from kayanos.kayanos_core.report.re_receivables_worklist.re_receivables_worklist import get_data as get_receivables_worklist_data

class TestCommercialReports(unittest.TestCase):
    
    @patch("kayanos.kayanos_core.report.re_customer_commercial_statement.re_customer_commercial_statement.frappe")
    def test_customer_statement(self, mock_frappe):
        mock_frappe.db.sql.side_effect = [
            # Events
            [{"name": "BE-001", "sales_agreement": "SA-001", "erpnext_invoice_ref": "SINV-001", "currency": "USD", "gross_invoiced_amount": 1000, "returned_amount": 0, "posting_date": "2026-01-01"}],
            # Payment Entries
            [{"name": "PE-001", "posting_date": "2026-01-02", "allocated_amount": 500}],
            # Journal Entries
            []
        ]
        
        data = get_customer_statement_data({"customer": "Cust A"})
        self.assertEqual(len(data), 2)
        
        self.assertEqual(data[0]["transaction_type"], "Billing Event")
        self.assertEqual(data[0]["invoiced_amount"], 1000)
        self.assertEqual(data[0]["balance"], 1000)
        
        self.assertEqual(data[1]["transaction_type"], "Payment Collection")
        self.assertEqual(data[1]["paid_amount"], 500)
        self.assertEqual(data[1]["balance"], 500)

    @patch("kayanos.kayanos_core.report.re_commercial_collection_summary.re_commercial_collection_summary.frappe")
    def test_collection_summary(self, mock_frappe):
        mock_frappe.db.escape.side_effect = lambda x: x
        mock_frappe.db.sql.side_effect = [
            # Agreements
            [{"sales_agreement": "SA-001", "customer": "Cust A", "contract_value": 5000, "currency": "USD"}],
            # Events Aggregate
            [{"invoiced": 1000, "collected": 500, "returned": 0, "outstanding": 500}]
        ]
        
        data = get_collection_summary_data({"customer": "Cust A"})
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["total_invoiced"], 1000)
        self.assertEqual(data[0]["total_collected"], 500)
        self.assertEqual(data[0]["total_outstanding"], 500)

    @patch("kayanos.kayanos_core.report.re_receivables_worklist.re_receivables_worklist.frappe")
    def test_receivables_worklist(self, mock_frappe):
        mock_frappe.db.escape.side_effect = lambda x: x
        mock_frappe.db.sql.return_value = [
            {"name": "BE-001", "due_date": "2026-01-01", "projected_balance": 500}
        ]
        
        data = get_receivables_worklist_data({"collection_status": "Unpaid"})
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "BE-001")
        self.assertEqual(data[0]["projected_balance"], 500)
