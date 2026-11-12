import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.ro_units import reload_filters_from_model
from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_user

MASTERS = ["AMC Customer", "RO Unit", "RO Model", "Service Part", "AMC Technician"]


class TestPermissions(IntegrationTestCase):
	def setUp(self):
		self.tech = make_user("p1.tech@example.com", "AMC Technician").name
		self.owner = make_user("p1.owner@example.com", "AMC Owner").name
		self.addCleanup(frappe.set_user, "Administrator")

	def test_technician_is_read_only(self):
		for dt in MASTERS:
			for ptype in ("create", "write", "delete"):
				self.assertFalse(frappe.has_permission(dt, ptype, user=self.tech), f"{dt} {ptype}")
			self.assertTrue(frappe.has_permission(dt, "read", user=self.tech), f"{dt} read")

	def test_technician_cannot_open_settings(self):
		self.assertFalse(frappe.has_permission("AMC Settings", "read", user=self.tech))

	def test_owner_has_full_access(self):
		for dt in MASTERS + ["AMC Settings"]:
			for ptype in ("read", "create", "write", "delete"):
				self.assertTrue(frappe.has_permission(dt, ptype, user=self.owner), f"{dt} {ptype}")

	def test_technician_cannot_create_via_api(self):
		frappe.set_user(self.tech)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "AMC Customer", "customer_name": "X", "mobile_no": "9876500002"}).insert()

	def test_technician_cannot_reload_filters(self):
		model = make_model("PermBrand", "P1", {"Perm Filter": 90})
		customer = make_customer("Perm Cust", "9876500003")
		unit = frappe.get_doc({"doctype": "RO Unit", "customer": customer.name, "ro_model": model.name}).insert()
		frappe.set_user(self.tech)
		with self.assertRaises(frappe.PermissionError):
			reload_filters_from_model(unit.name)

	def test_roles_exist(self):
		self.assertTrue(frappe.db.exists("Role", "AMC Owner"))
		self.assertTrue(frappe.db.exists("Role", "AMC Technician"))
