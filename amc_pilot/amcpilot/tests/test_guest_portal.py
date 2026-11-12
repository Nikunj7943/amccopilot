import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.guest_portal import build_portal_context, get_unit_by_token, request_service
from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_unit_simple


class TestGuestPortal(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("GuestBrand", "G1", {"Guest Filter": 90})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876900001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Guest Cust", "9876900001")
		)
		self.unit = make_unit_simple(self.customer.name, self.model.name, install_date="2026-01-01")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_lookup_by_token(self):
		found = get_unit_by_token(self.unit.qr_token)
		self.assertEqual(found.name, self.unit.name)

	def test_bad_token_returns_none(self):
		self.assertIsNone(get_unit_by_token("not-a-real-token"))
		self.assertIsNone(get_unit_by_token(""))
		self.assertIsNone(get_unit_by_token(None))

	def test_context_has_no_mobile_or_money(self):
		ctx = build_portal_context(self.unit)
		self.assertEqual(ctx["customer_name"], "Guest Cust")
		self.assertNotIn("mobile_no", ctx)
		self.assertNotIn("amount", ctx)
		self.assertTrue(ctx["filters_due"])

	def test_guest_can_request_service(self):
		frappe.set_user("Guest")
		result = request_service(self.unit.qr_token)
		self.assertEqual(result["status"], "requested")
		visit = frappe.get_doc("Service Visit", result["visit"])
		self.assertEqual(visit.ro_unit, self.unit.name)
		self.assertEqual(visit.visit_type, "Complaint")

	def test_second_request_same_day_does_not_duplicate(self):
		frappe.set_user("Guest")
		first = request_service(self.unit.qr_token)
		second = request_service(self.unit.qr_token)
		self.assertEqual(second["status"], "already_requested")
		self.assertEqual(second["visit"], first["visit"])

	def test_bad_token_request_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			request_service("no-such-token")
