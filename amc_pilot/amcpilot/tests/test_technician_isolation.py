import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_user


def make_unit(customer, model):
	return frappe.get_doc({"doctype": "RO Unit", "customer": customer, "ro_model": model}).insert()


def make_technician(name, user_email):
	user = make_user(user_email, "AMC Technician")
	if frappe.db.exists("AMC Technician", {"user": user.name}):
		return frappe.db.get_value("AMC Technician", {"user": user.name})
	tech = frappe.get_doc(
		{"doctype": "AMC Technician", "technician_name": name, "user": user.name}
	).insert(ignore_permissions=True)
	return tech.name


class TestTechnicianIsolation(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("IsoBrand", "I1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877300001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Iso Cust", "9877300001")
		)
		self.unit = make_unit(self.customer.name, self.model.name)

		self.tech_a = make_technician("Iso Tech A", "iso.tech.a@example.com")
		self.tech_b = make_technician("Iso Tech B", "iso.tech.b@example.com")
		self.user_a = "iso.tech.a@example.com"
		self.user_b = "iso.tech.b@example.com"
		self.owner = make_user("iso.owner@example.com", "AMC Owner").name

		self.visit_a = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": self.unit.name,
				"technician": self.tech_a,
				"scheduled_date": "2026-02-01",
			}
		).insert(ignore_permissions=True)
		self.visit_b = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": self.unit.name,
				"technician": self.tech_b,
				"scheduled_date": "2026-02-02",
			}
		).insert(ignore_permissions=True)
		self.visit_unassigned = frappe.get_doc(
			{"doctype": "Service Visit", "ro_unit": self.unit.name, "scheduled_date": "2026-02-03"}
		).insert(ignore_permissions=True)

		self.addCleanup(frappe.set_user, "Administrator")

	def test_technician_a_list_shows_only_own(self):
		frappe.set_user(self.user_a)
		names = frappe.get_list("Service Visit", pluck="name")
		self.assertIn(self.visit_a.name, names)
		self.assertNotIn(self.visit_b.name, names)
		self.assertNotIn(self.visit_unassigned.name, names)

	def test_technician_a_cannot_get_doc_b(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Service Visit", self.visit_b.name).check_permission("read")

	def test_technician_a_has_permission_false_on_b(self):
		self.assertFalse(frappe.has_permission("Service Visit", "read", doc=self.visit_b.name, user=self.user_a))
		self.assertTrue(frappe.has_permission("Service Visit", "read", doc=self.visit_a.name, user=self.user_a))

	def test_technician_cannot_edit_b_via_api(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("Service Visit", self.visit_b.name)
			doc.notes = "trying to edit someone else's visit"
			doc.save()

	def test_technician_cannot_reassign_technician_field(self):
		frappe.set_user(self.user_a)
		doc = frappe.get_doc("Service Visit", self.visit_a.name)
		doc.technician = self.tech_b
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_technician_cannot_edit_completed_visit(self):
		# Owner completes visit_a first.
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Service Visit", self.visit_a.name)
		doc.status = "Completed"
		doc.no_parts_used = 1
		doc.save()

		frappe.set_user(self.user_a)
		doc = frappe.get_doc("Service Visit", self.visit_a.name)
		doc.notes = "trying to edit after completion"
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_owner_has_permission_true_not_falsy(self):
		"""Regression: a has_permission hook that returns None instead of True
		is treated as an explicit DENY by Frappe (frappe/permissions.py
		has_controller_permissions: `if not controller_permission: return
		bool(controller_permission)`), even for a privileged user. This must
		come back truthy for the Owner on every visit, assigned or not."""
		self.assertTrue(frappe.has_permission("Service Visit", "read", doc=self.visit_a.name, user=self.owner))
		self.assertTrue(frappe.has_permission("Service Visit", "read", doc=self.visit_b.name, user=self.owner))
		self.assertTrue(
			frappe.has_permission("Service Visit", "read", doc=self.visit_unassigned.name, user=self.owner)
		)

	def test_owner_can_actually_open_a_visit_via_get_doc_and_check_permission(self):
		frappe.set_user(self.owner)
		doc = frappe.get_doc("Service Visit", self.visit_a.name)
		doc.check_permission("read")  # must not raise

	def test_owner_sees_all_visits(self):
		frappe.set_user(self.owner)
		names = frappe.get_list("Service Visit", pluck="name")
		self.assertIn(self.visit_a.name, names)
		self.assertIn(self.visit_b.name, names)
		self.assertIn(self.visit_unassigned.name, names)

	def test_unassigned_visits_hidden_from_technicians(self):
		frappe.set_user(self.user_a)
		names = frappe.get_list("Service Visit", pluck="name")
		self.assertNotIn(self.visit_unassigned.name, names)

	def test_guest_qr_created_visit_still_works(self):
		"""The guest QR flow and Activate both insert with ignore_permissions=True
		as Guest/Administrator - neither has an AMC Technician record, so the
		isolation rule must not block them."""
		frappe.set_user("Guest")
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": self.unit.name,
				"visit_type": "Complaint",
				"scheduled_date": "2026-02-04",
			}
		)
		visit.insert(ignore_permissions=True)  # must not raise
		self.assertTrue(visit.name)
