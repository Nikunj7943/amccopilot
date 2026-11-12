import hashlib
import hmac
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.payments import (
	create_payment,
	get_payment_options,
	mark_paid_manually,
	upi_link,
	verify_and_mark_paid,
)
from amc_pilot.amcpilot.tests.utils import make_contract, make_customer, make_model, make_unit_simple


class TestPayments(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("PayBrand", "P1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876800001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Pay Cust", "9876800001")
		)
		self.unit = make_unit_simple(self.customer.name, self.model.name)
		self.contract = make_contract(self.unit.name, self.customer.name, amount=2500)

		settings = frappe.get_single("AMC Settings")
		self.addCleanup(self._restore_settings, settings.razorpay_key_id, settings.business_upi_id)
		settings.razorpay_key_id = ""
		settings.business_upi_id = "shop@upi"
		settings.business_name = "Test Shop"
		settings.save()

	def _restore_settings(self, key_id, upi):
		settings = frappe.get_single("AMC Settings")
		settings.razorpay_key_id = key_id
		settings.business_upi_id = upi
		settings.save()

	def test_create_payment(self):
		name = create_payment(self.contract.name)
		doc = frappe.get_doc("AMC Payment", name)
		self.assertEqual(doc.status, "Pending")
		self.assertEqual(doc.amount, 2500)

	def test_upi_link_built_from_settings(self):
		link = upi_link(2500, "test note")
		self.assertTrue(link.startswith("upi://pay?"))
		self.assertIn("pa=shop%40upi", link)
		self.assertIn("am=2500.00", link)

	def test_without_razorpay_keys_falls_back_to_upi(self):
		name = create_payment(self.contract.name)
		options = get_payment_options(name)
		self.assertEqual(options["method"], "upi")
		self.assertTrue(options["upi_link"].startswith("upi://pay?"))

	def test_mark_paid_manually_updates_contract_status(self):
		name = create_payment(self.contract.name)
		mark_paid_manually(name, method="Cash")
		doc = frappe.get_doc("AMC Payment", name)
		self.assertEqual(doc.status, "Paid")
		self.assertEqual(doc.method, "Cash")
		self.assertTrue(doc.paid_on)
		self.contract.reload()
		self.assertEqual(self.contract.payment_status, "Paid")

	def test_razorpay_order_created_when_keys_set(self):
		settings = frappe.get_single("AMC Settings")
		settings.razorpay_key_id = "rzp_test_demo"
		settings.razorpay_key_secret = "demo_secret"
		settings.save()

		mock_response = MagicMock(status_code=200)
		mock_response.json.return_value = {"id": "order_demo123"}
		with patch("requests.post", return_value=mock_response) as mock_post:
			name = create_payment(self.contract.name)
			options = get_payment_options(name)

		self.assertEqual(options["method"], "razorpay")
		self.assertEqual(options["order_id"], "order_demo123")
		self.assertEqual(options["key_id"], "rzp_test_demo")
		mock_post.assert_called_once()

	def test_razorpay_signature_verified(self):
		settings = frappe.get_single("AMC Settings")
		settings.razorpay_key_id = "rzp_test_demo"
		settings.razorpay_key_secret = "demo_secret"
		settings.save()

		name = create_payment(self.contract.name)
		frappe.db.set_value("AMC Payment", name, "razorpay_order_id", "order_demo123")

		good_sig = hmac.new(b"demo_secret", b"order_demo123|pay_demo456", hashlib.sha256).hexdigest()
		verify_and_mark_paid(name, "pay_demo456", "order_demo123", good_sig)
		self.assertEqual(frappe.db.get_value("AMC Payment", name, "status"), "Paid")

	def test_razorpay_bad_signature_rejected(self):
		settings = frappe.get_single("AMC Settings")
		settings.razorpay_key_id = "rzp_test_demo"
		settings.razorpay_key_secret = "demo_secret"
		settings.save()

		name = create_payment(self.contract.name)
		frappe.db.set_value("AMC Payment", name, "razorpay_order_id", "order_demo123")
		with self.assertRaises(frappe.ValidationError):
			verify_and_mark_paid(name, "pay_demo456", "order_demo123", "wrong-signature")
		self.assertEqual(frappe.db.get_value("AMC Payment", name, "status"), "Pending")

	def test_technician_cannot_mark_paid(self):
		from amc_pilot.amcpilot.tests.utils import make_user

		tech = make_user("pay.tech@example.com", "AMC Technician").name
		name = create_payment(self.contract.name)
		frappe.set_user(tech)
		try:
			with self.assertRaises(frappe.PermissionError):
				mark_paid_manually(name)
		finally:
			frappe.set_user("Administrator")
