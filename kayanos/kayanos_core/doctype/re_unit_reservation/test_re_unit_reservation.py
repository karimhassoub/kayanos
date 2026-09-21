import frappe
import unittest
import uuid
import threading
from unittest import mock
from frappe.utils import add_to_date, now_datetime
from frappe.exceptions import ValidationError
from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import expire_reservations

class IntegrationTestREReservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.flags.in_test = True
        frappe.db.set_single_value("RE Reservation Settings", "default_reservation_duration_hours", 48.0)
        
        proj_name = frappe.db.get_value("Project", {"project_name": "TEST-RES-PROJ"})
        if not proj_name:
            proj = frappe.get_doc({"doctype": "Project", "project_name": "TEST-RES-PROJ"})
            proj.flags.ignore_mandatory = True
            proj.flags.ignore_links = True
            proj.insert(ignore_permissions=True, ignore_links=True)
            proj_name = proj.name
        cls.proj_name = proj_name
            
        if not frappe.db.exists("RE Project Profile", {"project": proj_name}):
            doc = frappe.get_doc({
                "doctype": "RE Project Profile",
                "project": proj_name,
                "ownership_type": "Internal",
                "sales_authorized": 1
            })
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.commit() # Ensure visible to threads

    def create_test_deal(self):
        doc = frappe.get_doc({
            "doctype": "CRM Deal",
            "status": "Open"
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True, ignore_links=True)
        return doc.name

    def create_test_unit(self, suffix, phase_auth=1):
        phase_type = frappe.db.exists("RE Phase Type", "Test Phase Type") or frappe.get_doc({"doctype": "RE Phase Type", "type_name": "Test Phase Type"}).insert(ignore_permissions=True).name
        prop_type = frappe.db.exists("RE Property Type", "Test Prop Type") or frappe.get_doc({"doctype": "RE Property Type", "type_name": "Test Prop Type"}).insert(ignore_permissions=True).name
        unit_type = frappe.db.exists("RE Unit Type", "Test Unit Type") or frappe.get_doc({"doctype": "RE Unit Type", "type_name": "Test Unit Type", "category": "Residential"}).insert(ignore_permissions=True).name
        
        phase = frappe.get_doc({
            "doctype": "RE Phase",
            "project": self.proj_name,
            "phase_name": "PH-" + suffix,
            "phase_type": phase_type,
            "sales_authorized": phase_auth
        })
        phase.flags.ignore_links = True
        phase.insert(ignore_permissions=True, ignore_links=True)
        
        prop = frappe.get_doc({
            "doctype": "RE Property",
            "phase": phase.name,
            "property_name": "PR-" + suffix,
            "property_type": prop_type
        })
        prop.flags.ignore_links = True
        prop.insert(ignore_permissions=True, ignore_links=True)
        
        unit = frappe.get_doc({
            "doctype": "RE Unit",
            "property": prop.name,
            "unit_number": "UN-" + suffix,
            "unit_type": unit_type,
            "lifecycle_status": "Active",
            "availability_status": "Available"
        })
        unit.flags.ignore_links = True
        unit.insert(ignore_permissions=True, ignore_links=True)
        return unit.name

    def test_01_draft_to_active(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({
            "doctype": "RE Unit Reservation",
            "crm_deal": deal,
            "unit": unit
        })
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        self.assertEqual(res.status, "Draft")
        
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        self.assertEqual(res.status, "Active")
        
        unit_status = frappe.db.get_value("RE Unit", unit, "availability_status")
        self.assertEqual(unit_status, "Reserved")
        self.assertIsNotNone(res.expiry_time)

    def test_02_unit_uniqueness(self):
        deal1 = self.create_test_deal()
        deal2 = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res1 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal1, "unit": unit})
        res1.flags.ignore_links = True
        res1.insert(ignore_permissions=True, ignore_links=True)
        res1.status = "Active"
        res1.flags.ignore_links = True
        res1.save()
        
        res2 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal2, "unit": unit})
        res2.flags.ignore_links = True
        res2.insert(ignore_permissions=True, ignore_links=True)
        res2.status = "Active"
        res2.flags.ignore_links = True
        self.assertRaises(frappe.exceptions.ValidationError, res2.save)

    def test_03_deal_uniqueness(self):
        deal = self.create_test_deal()
        unit1 = self.create_test_unit(str(uuid.uuid4())[:8])
        unit2 = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res1 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit1})
        res1.flags.ignore_links = True
        res1.insert(ignore_permissions=True, ignore_links=True)
        res1.status = "Active"
        res1.flags.ignore_links = True
        res1.save()
        
        res2 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit2})
        res2.flags.ignore_links = True
        res2.insert(ignore_permissions=True, ignore_links=True)
        res2.status = "Active"
        res2.flags.ignore_links = True
        self.assertRaises(frappe.exceptions.ValidationError, res2.save)

    def test_04_historical_reservations(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res1 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res1.flags.ignore_links = True
        res1.insert(ignore_permissions=True, ignore_links=True)
        res1.status = "Active"
        res1.flags.ignore_links = True
        res1.save()
        
        res1.status = "Expired"
        res1.flags.ignore_links = True
        res1.save()
        
        res2 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res2.flags.ignore_links = True
        res2.insert(ignore_permissions=True, ignore_links=True)
        res2.status = "Active"
        res2.flags.ignore_links = True
        res2.save()
        self.assertEqual(res2.status, "Active")

    def test_05_cancellation(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        res.status = "Cancelled"
        res.flags.ignore_links = True
        res.save()
        self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Available")

    def test_06_expiration_job(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        res.db_set("expiry_time", add_to_date(now_datetime(), days=-1))
        
        expire_reservations()
        res.reload()
        self.assertEqual(res.status, "Expired")
        self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Available")

    def test_07_sales_authorization_blocked(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        phase_name = frappe.db.get_value("RE Property", frappe.db.get_value("RE Unit", unit, "property"), "phase")
        frappe.db.set_value("RE Phase", phase_name, "sales_authorized", 0)
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        
        res.status = "Active"
        res.flags.ignore_links = True
        self.assertRaises(frappe.exceptions.ValidationError, res.save)

    def test_08_immutability(self):
        deal = self.create_test_deal()
        unit1 = self.create_test_unit(str(uuid.uuid4())[:8])
        unit2 = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit1})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        res.unit = unit2
        res.flags.ignore_links = True
        self.assertRaises(frappe.exceptions.ValidationError, res.save)

    def test_09_concurrency(self):
        # REAL CONCURRENCY TEST
        deal1 = self.create_test_deal()
        deal2 = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        frappe.db.commit() # Commit so background threads see records

        results = {}

        def attempt_reservation(deal, thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                res = f2.get_doc({
                    "doctype": "RE Unit Reservation",
                    "crm_deal": deal,
                    "unit": unit
                })
                res.flags.ignore_links = True
                res.insert(ignore_permissions=True, ignore_links=True)
                res.status = "Active"
                res.save()
                f2.db.commit()
                results[thread_id] = "Success"
            except Exception as e:
                f2.db.rollback()
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        t1 = threading.Thread(target=attempt_reservation, args=(deal1, "T1"))
        t2 = threading.Thread(target=attempt_reservation, args=(deal2, "T2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = list(results.values()).count("Success")
        self.assertEqual(successes, 1, f"Expected exactly 1 success, got {successes}. Results: {results}")

    def test_09b_deal_concurrency(self):
        # REAL CONCURRENCY TEST for Deal constraint
        deal = self.create_test_deal()
        unit1 = self.create_test_unit(str(uuid.uuid4())[:8])
        unit2 = self.create_test_unit(str(uuid.uuid4())[:8])
        frappe.db.commit() # Commit so background threads see records

        results = {}

        def attempt_reservation(deal, unit, thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                res = f2.get_doc({
                    "doctype": "RE Unit Reservation",
                    "crm_deal": deal,
                    "unit": unit
                })
                res.flags.ignore_links = True
                res.insert(ignore_permissions=True, ignore_links=True)
                res.status = "Active"
                res.save()
                f2.db.commit()
                results[thread_id] = "Success"
            except Exception as e:
                f2.db.rollback()
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        t1 = threading.Thread(target=attempt_reservation, args=(deal, unit1, "T1"))
        t2 = threading.Thread(target=attempt_reservation, args=(deal, unit2, "T2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = list(results.values()).count("Success")
        self.assertEqual(successes, 1, f"Expected exactly 1 success, got {successes}. Results: {results}")

    def test_10_guest_permission(self):
        frappe.set_user("Guest")
        try:
            res = frappe.get_doc({
                "doctype": "RE Unit Reservation",
                "crm_deal": frappe.db.get_value("CRM Deal", {}),
                "unit": "ANY"
            })
            self.assertRaises(frappe.PermissionError, res.insert)
        finally:
            frappe.set_user("Administrator")

    def test_11_crm_integrity(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        deal_doc_before = frappe.get_doc("CRM Deal", deal)
        original_status = deal_doc_before.status
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        deal_doc_mid = frappe.get_doc("CRM Deal", deal)
        self.assertEqual(deal_doc_mid.status, original_status)
        
        res.status = "Cancelled"
        res.flags.ignore_links = True
        res.save()
        
        deal_doc_after = frappe.get_doc("CRM Deal", deal)
        self.assertEqual(deal_doc_after.status, original_status)

    def test_12_rollback(self):
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        
        frappe.db.commit() # Commit the creation of deal, unit, and draft reservation so they survive the rollback
        
        # Monkey patch db_update to simulate a failure AFTER unit was marked Reserved in validate()
        original_db_update = res.db_update
        def mock_db_update(*args, **kwargs):
            raise ValueError("Simulated DB Update Failure")
            
        res.db_update = mock_db_update
        
        res.status = "Active"
        res.flags.ignore_links = True
        try:
            res.save()
        except ValueError:
            frappe.db.rollback() # Standard Frappe request error handler behavior
            
        # Verify no partial state!
        self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Available")
        self.assertEqual(frappe.db.get_value("RE Unit Reservation", res.name, "status"), "Draft")

    # ==================================================
    # PHASE 5A TESTS
    # ==================================================
    
    def test_13_phase5a_conversion_success(self):
        # TEST 1 & TEST 2 & TEST 9
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        deal_doc_before = frappe.get_doc("CRM Deal", deal)
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        # Test 1 & 2: Convert
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        convert_reservation(res.name)
        
        res.reload()
        self.assertEqual(res.status, "Converted")
        self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Reserved")
        
        # Test 9: CRM unchanged
        deal_doc_after = frappe.get_doc("CRM Deal", deal)
        self.assertEqual(deal_doc_after.status, deal_doc_before.status)
        self.assertEqual(deal_doc_after.modified, deal_doc_before.modified)
        
    def test_14_phase5a_converted_idempotency(self):
        # TEST 3
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        convert_reservation(res.name)
        
        with self.assertRaises(frappe.exceptions.ValidationError) as context:
            convert_reservation(res.name)
        self.assertIn("already converted", str(context.exception))
        
    def test_15_phase5a_cancelled_expired_draft(self):
        # TEST 4, 5, 6
        deal1 = self.create_test_deal()
        unit1 = self.create_test_unit(str(uuid.uuid4())[:8])
        res1 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal1, "unit": unit1})
        res1.flags.ignore_links = True
        res1.insert(ignore_permissions=True, ignore_links=True)
        res1.status = "Active"
        res1.flags.ignore_links = True
        res1.save()
        res1.status = "Cancelled"
        res1.save()
        
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            convert_reservation(res1.name)
            
        deal2 = self.create_test_deal()
        unit2 = self.create_test_unit(str(uuid.uuid4())[:8])
        res2 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal2, "unit": unit2})
        res2.flags.ignore_links = True
        res2.insert(ignore_permissions=True, ignore_links=True)
        res2.status = "Active"
        res2.flags.ignore_links = True
        res2.save()
        res2.status = "Expired"
        res2.save()
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            convert_reservation(res2.name)
            
        deal3 = self.create_test_deal()
        unit3 = self.create_test_unit(str(uuid.uuid4())[:8])
        res3 = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal3, "unit": unit3})
        res3.flags.ignore_links = True
        res3.insert(ignore_permissions=True, ignore_links=True)
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            convert_reservation(res3.name)
            
    def test_16_phase5a_missing(self):
        # TEST 7
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        with self.assertRaises(frappe.exceptions.ValidationError):
            convert_reservation("INVALID_NAME")
            
    def test_17_phase5a_unit_not_reserved(self):
        # TEST 8
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        # force unit to available to simulate error
        frappe.db.set_value("RE Unit", unit, "availability_status", "Available")
        
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        with self.assertRaises(frappe.exceptions.ValidationError):
            convert_reservation(res.name)
            
    def test_18_phase5a_no_customer_accounting(self):
        # TEST 10 & 11
        customer_count_before = frappe.db.count("Customer")
        si_count_before = frappe.db.count("Sales Invoice")
        pe_count_before = frappe.db.count("Payment Entry")
        
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
        convert_reservation(res.name)
        
        self.assertEqual(frappe.db.count("Customer"), customer_count_before)
        self.assertEqual(frappe.db.count("Sales Invoice"), si_count_before)
        self.assertEqual(frappe.db.count("Payment Entry"), pe_count_before)
        
    def test_19_phase5a_concurrency_conversion(self):
        # TEST 12
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        frappe.db.commit()
        results = {}
        
        def attempt_conversion(res_name, thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
                convert_reservation(res_name)
                f2.db.commit()
                results[thread_id] = "Success"
            except Exception as e:
                f2.db.rollback()
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        t1 = threading.Thread(target=attempt_conversion, args=(res.name, "T1"))
        t2 = threading.Thread(target=attempt_conversion, args=(res.name, "T2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = list(results.values()).count("Success")
        self.assertEqual(successes, 1, f"Expected exactly 1 success, got {successes}. Results: {results}")

    def test_20_phase5a_concurrency_expiration_race(self):
        # TEST 13
        deal = self.create_test_deal()
        unit = self.create_test_unit(str(uuid.uuid4())[:8])
        
        res = frappe.get_doc({"doctype": "RE Unit Reservation", "crm_deal": deal, "unit": unit})
        res.flags.ignore_links = True
        res.insert(ignore_permissions=True, ignore_links=True)
        res.status = "Active"
        res.flags.ignore_links = True
        res.save()
        
        res.db_set("expiry_time", add_to_date(now_datetime(), days=-1))
        frappe.db.commit()
        results = {}

        def attempt_conversion(res_name, thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import convert_reservation
                convert_reservation(res_name)
                f2.db.commit()
                results[thread_id] = "Converted"
            except Exception as e:
                f2.db.rollback()
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        def attempt_expiration(thread_id):
            import frappe as f2
            f2.connect("kayanos.localhost")
            try:
                from kayanos.kayanos_core.doctype.re_unit_reservation.re_unit_reservation import expire_reservations
                expire_reservations()
                results[thread_id] = "Expired Job Ran"
            except Exception as e:
                results[thread_id] = str(e)
            finally:
                f2.destroy()

        t1 = threading.Thread(target=attempt_conversion, args=(res.name, "ConvertThread"))
        t2 = threading.Thread(target=attempt_expiration, args=("ExpireThread",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        frappe.db.rollback() # clear any local transaction state
        res.reload()
        
        self.assertIn(res.status, ["Converted", "Expired"])
        if res.status == "Converted":
            self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Reserved")
        else:
            self.assertEqual(frappe.db.get_value("RE Unit", unit, "availability_status"), "Available")

