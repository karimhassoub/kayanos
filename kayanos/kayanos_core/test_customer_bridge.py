import frappe
import unittest
import uuid
from kayanos.kayanos_core.customer_bridge import get_or_create_customer

class TestCustomerBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.flags.in_test = True
        
    def create_test_deal(self, organization=None, lead_name=None, territory=None):
        doc = frappe.get_doc({
            "doctype": "CRM Deal",
            "status": "Open",
            "organization": organization,
            "lead_name": lead_name,
            "territory": territory
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True, ignore_links=True)
        return doc.name

    def test_01_create_company_customer(self):
        org_name = "Test Org " + str(uuid.uuid4())[:8]
        deal = self.create_test_deal(organization=org_name)
        
        customer_name = get_or_create_customer(deal)
        
        self.assertTrue(frappe.db.exists("Customer", customer_name))
        
        customer = frappe.get_doc("Customer", customer_name)
        self.assertEqual(customer.customer_name, org_name)
        self.assertEqual(customer.customer_type, "Company")
        
        # Verify it's linked to the deal if field exists
        deal_doc = frappe.get_doc("CRM Deal", deal)
        if deal_doc.meta.has_field("erpnext_customer"):
            self.assertEqual(deal_doc.erpnext_customer, customer_name)

    def test_02_create_individual_customer(self):
        lead_name = "Test Lead " + str(uuid.uuid4())[:8]
        deal = self.create_test_deal(lead_name=lead_name)
        
        customer_name = get_or_create_customer(deal)
        
        self.assertTrue(frappe.db.exists("Customer", customer_name))
        
        customer = frappe.get_doc("Customer", customer_name)
        self.assertEqual(customer.customer_name, lead_name)
        self.assertEqual(customer.customer_type, "Individual")

    def test_03_existing_customer_by_name_throws_error(self):
        org_name = "Test Org Existing " + str(uuid.uuid4())[:8]
        # Create customer directly
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": org_name,
            "customer_type": "Company"
        })
        cust.flags.ignore_mandatory = True
        cust.insert(ignore_permissions=True)
        
        deal = self.create_test_deal(organization=org_name)
        with self.assertRaises(frappe.exceptions.ValidationError) as context:
            get_or_create_customer(deal)
        self.assertIn("already exists", str(context.exception))
        
    def test_04_missing_deal_raises_error(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            get_or_create_customer("INVALID_DEAL_NAME_123")
            
    def test_05_no_org_or_lead_raises_error(self):
        deal = self.create_test_deal() # neither org nor lead
        with self.assertRaises(frappe.exceptions.ValidationError):
            get_or_create_customer(deal)
            
    def test_06_stale_link_raises_error(self):
        org_name = "Test Org Stale " + str(uuid.uuid4())[:8]
        deal = self.create_test_deal(organization=org_name)
        
        # Manually force a stale link if field exists
        deal_doc = frappe.get_doc("CRM Deal", deal)
        if deal_doc.meta.has_field("erpnext_customer"):
            deal_doc.db_set("erpnext_customer", "GHOST_CUSTOMER_999")
            
            with self.assertRaises(frappe.exceptions.ValidationError) as context:
                get_or_create_customer(deal)
            self.assertIn("no longer exists", str(context.exception))

    def test_07_concurrency_prevention(self):
        import threading
        
        org_name = "Test Concurrent " + str(uuid.uuid4())[:8]
        deal = self.create_test_deal(organization=org_name)
        frappe.db.commit() # Ensure deal is available to threads
        
        results = {}
        def attempt_bridge(thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                from kayanos.kayanos_core.customer_bridge import get_or_create_customer
                get_or_create_customer(deal)
                f2.db.commit()
                results[thread_id] = "Success"
            except Exception as e:
                f2.db.rollback()
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        t1 = threading.Thread(target=attempt_bridge, args=("T1",))
        t2 = threading.Thread(target=attempt_bridge, args=("T2",))
        t1.start()
        t2.start()
        # Wait for threads to complete
        t1.join()
        t2.join()

        # Both threads should succeed: one creates, the second reads the newly committed link
        self.assertEqual(results["T1"], "Success")
        self.assertEqual(results["T2"], "Success")

        # Verify exact number of Customers created
        import frappe as f3
        count = f3.db.count("Customer", {"customer_name": org_name})
        self.assertEqual(count, 1, "There should be exactly 1 customer created.")

        # Verify final erpnext_customer link on the deal
        final_customer_link = f3.db.get_value("CRM Deal", deal, "erpnext_customer")
        self.assertIsNotNone(final_customer_link, "CRM Deal should have erpnext_customer populated.")
        
        # Verify no orphan or duplicate
        # (Already verified by count == 1 and link being valid)
        customer_doc = f3.get_doc("Customer", final_customer_link)
        self.assertEqual(customer_doc.customer_name, org_name)

    def test_08_existing_valid_link_reused(self):
        org_name = "Test Org Valid Link " + str(uuid.uuid4())[:8]
        deal = self.create_test_deal(organization=org_name)
        
        customer_name = get_or_create_customer(deal)
        
        # Second call should reuse the same link
        customer_name2 = get_or_create_customer(deal)
        self.assertEqual(customer_name, customer_name2)
        
        count = frappe.db.count("Customer", {"customer_name": org_name})
        self.assertEqual(count, 1)
