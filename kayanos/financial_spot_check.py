import sys
from unittest.mock import MagicMock
m = MagicMock()
m.utils.flt = lambda x, p=None: round(float(x), p) if p else float(x)
sys.modules['frappe'] = m
sys.modules['frappe.utils'] = m.utils
from kayanos.kayanos_core.report.re_customer_commercial_statement.re_customer_commercial_statement import get_data as statement_data
from kayanos.kayanos_core.report.re_commercial_collection_summary.re_commercial_collection_summary import get_data as summary_data

def test_financial_integrity():
    # Setup Frappe DB Mock
    def db_escape(x): return str(x)
    m.db.escape.side_effect = db_escape
    
    # MOCK DATA FOR STATEMENT
    def statement_sql_mock(query, params, as_dict):
        if "tabRE Billing Event" in query:
            # 2 Events: One for 1000, one for 2000
            return [
                {"name": "BE-1", "sales_agreement": "SA-1", "erpnext_invoice_ref": "INV-1", "currency": "USD", "gross_invoiced_amount": 1000, "returned_amount": 0, "posting_date": "2026-01-01"},
                {"name": "BE-2", "sales_agreement": "SA-1", "erpnext_invoice_ref": "INV-2", "currency": "USD", "gross_invoiced_amount": 2000, "returned_amount": 500, "posting_date": "2026-01-05"} # Partial return
            ]
        if "tabPayment Entry Reference" in query:
            if params[0] == "INV-1":
                # Partial allocation
                return [{"name": "PE-1", "posting_date": "2026-01-02", "allocated_amount": 400}]
            if params[0] == "INV-2":
                # Full settlement minus return
                return [{"name": "PE-2", "posting_date": "2026-01-06", "allocated_amount": 1500}]
        if "tabJournal Entry Account" in query:
            if params[0] == "INV-1":
                # Adjustment
                return [{"name": "JE-1", "posting_date": "2026-01-03", "credit_in_account_currency": 100}]
            return []
        return []
        
    m.db.sql.side_effect = statement_sql_mock
    
    # Run Statement
    data = statement_data({"customer": "Cust A", "company": "Co A"})
    
    print("STATEMENT TESTS:")
    for row in data:
        print(f"Date: {row['posting_date']}, Type: {row['transaction_type']}, Invoiced: {row['invoiced_amount']}, Paid: {row['paid_amount']}, Balance: {row['balance']}")
        
    # Verify running balance
    assert data[-1]['balance'] == 500.0, f"Expected 500.0, got {data[-1]['balance']}"
    print("Statement Running Balance: PASS\n")
    
    # MOCK DATA FOR SUMMARY
    def summary_sql_mock(query, params=None, as_dict=False):
        if "tabRE Sales Agreement" in query:
            return [{"sales_agreement": "SA-1", "customer": "Cust A", "contract_value": 3000, "currency": "USD"}]
        if "tabRE Billing Event" in query:
            # Aggregate: invoiced = 3000, collected = 1900 + 100 = 2000, returned = 500, outstanding = 500
            return [{"invoiced": 3000, "collected": 2000, "returned": 500, "outstanding": 500}]
        return []
        
    m.db.sql.side_effect = summary_sql_mock
    sum_data = summary_data({"customer": "Cust A", "company": "Co A"})
    
    print("SUMMARY TESTS:")
    row = sum_data[0]
    print(f"Invoiced: {row['total_invoiced']}, Collected: {row['total_collected']}, Returned: {row['total_returned']}, Outstanding: {row['total_outstanding']}")
    assert row['total_invoiced'] == 3000
    assert row['total_collected'] == 2000
    assert row['total_returned'] == 500
    assert row['total_outstanding'] == 500
    print("Summary Totals: PASS\n")

if __name__ == "__main__":
    test_financial_integrity()
