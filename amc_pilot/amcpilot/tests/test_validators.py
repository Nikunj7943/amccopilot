import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.validators import normalize_mobile
from amc_pilot.amcpilot.tests.utils import make_customer


class TestMobileNormalisation(IntegrationTestCase):
	def test_valid_plain(self):
		self.assertEqual(normalize_mobile("9876543210"), "9876543210")

	def test_plus_91(self):
		self.assertEqual(normalize_mobile("+91 98765-43210"), "9876543210")

	def test_91_prefix(self):
		self.assertEqual(normalize_mobile("919876543210"), "9876543210")

	def test_leading_zero(self):
		self.assertEqual(normalize_mobile("09876543210"), "9876543210")

	def test_spaces_and_dashes(self):
		self.assertEqual(normalize_mobile(" 98765 - 43210 "), "9876543210")

	def test_number_starting_with_91_is_not_stripped(self):
		self.assertEqual(normalize_mobile("9123456789"), "9123456789")

	def test_too_short(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mobile("98765")

	def test_too_long(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mobile("98765432101")

	def test_starts_with_5(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mobile("5876543210")

	def test_letters(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_mobile("98765abcde")

	def test_empty_optional_and_required(self):
		self.assertIsNone(normalize_mobile(""))
		self.assertIsNone(normalize_mobile(None))
		with self.assertRaises(frappe.ValidationError):
			normalize_mobile("", required=True)


class TestCustomerMobile(IntegrationTestCase):
	def test_customer_mobile_is_stored_normalised(self):
		customer = make_customer("Norm", "+91 98765 43211", alt_mobile="09876543212")
		self.assertEqual(customer.mobile_no, "9876543211")
		self.assertEqual(customer.alt_mobile, "9876543212")

	def test_invalid_customer_mobile_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_customer("Bad", "12345")

	def test_customer_mobile_unique(self):
		make_customer("First", "9876543213")
		with self.assertRaises(frappe.ValidationError):
			make_customer("Second", "+91 9876543213")  # same number after normalisation

	def test_customer_naming(self):
		self.assertTrue(make_customer("Named", "9876543214").name.startswith("CUST-"))

	def test_technician_and_settings_mobile(self):
		tech = frappe.get_doc(
			{"doctype": "AMC Technician", "technician_name": "T1", "mobile_no": "+919876543215"}
		).insert()
		self.assertEqual(tech.mobile_no, "9876543215")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "AMC Technician", "technician_name": "T2", "mobile_no": "123"}).insert()

		settings = frappe.get_single("AMC Settings")
		settings.business_name = "Test Business"
		settings.owner_mobile = "09876543216"
		settings.save()
		self.assertEqual(settings.owner_mobile, "9876543216")

	def test_technicians_without_user_do_not_clash(self):
		for n in ("A", "B"):
			frappe.get_doc({"doctype": "AMC Technician", "technician_name": f"No User {n}"}).insert()
