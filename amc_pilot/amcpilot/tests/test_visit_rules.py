import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_part


def make_unit(customer, model):
	return frappe.get_doc({"doctype": "RO Unit", "customer": customer, "ro_model": model}).insert()


class TestPartsRule(IntegrationTestCase):
	"""G1: a visit cannot become Completed with an empty Parts Used table
	unless no_parts_used is ticked. Checked through the Document API (which is
	exactly what the form, a script and /api/resource all go through)."""

	def setUp(self):
		self.model = make_model("RuleBrand", "R1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877100001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Rule Cust", "9877100001")
		)
		self.unit = make_unit(self.customer.name, self.model.name)
		make_part("Rule Part", "Other")

	def _visit(self, **kw):
		return frappe.get_doc(
			{"doctype": "Service Visit", "ro_unit": self.unit.name, "scheduled_date": "2026-02-01", **kw}
		).insert()

	def test_blocked_without_parts_and_without_flag(self):
		visit = self._visit()
		visit.status = "Completed"
		with self.assertRaises(frappe.ValidationError):
			visit.save()

	def test_allowed_with_no_parts_used_flag(self):
		visit = self._visit(no_parts_used=1)
		visit.status = "Completed"
		visit.save()  # must not raise
		self.assertEqual(visit.status, "Completed")

	def test_allowed_with_a_part_row(self):
		visit = self._visit(parts_used=[{"service_part": "Rule Part", "qty": 1, "rate": 10}])
		visit.status = "Completed"
		visit.save()
		self.assertEqual(visit.status, "Completed")

	def test_blocked_via_direct_db_insert_path_too(self):
		"""Insert straight through frappe.get_doc().insert() with status already
		Completed - same code path an API/import call would use."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Service Visit",
					"ro_unit": self.unit.name,
					"scheduled_date": "2026-02-01",
					"status": "Completed",
				}
			).insert()

	def test_scheduled_visit_with_no_parts_is_fine(self):
		visit = self._visit()  # status defaults to Scheduled; rule only applies to Completed
		self.assertEqual(visit.status, "Scheduled")
