import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from amc_pilot.amcpilot.services.amc_contracts import activate_contract, cancel_contract, generate_scheduled_visits
from amc_pilot.amcpilot.tests.utils import make_customer, make_model


def make_unit(customer, model):
	return frappe.get_doc({"doctype": "RO Unit", "customer": customer, "ro_model": model}).insert()


class TestContractScheduling(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("SchedBrand", "S1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877200001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Sched Cust", "9877200001")
		)
		self.unit = make_unit(self.customer.name, self.model.name)

	def _contract(self, visits_included=4):
		return frappe.get_doc(
			{
				"doctype": "AMC Contract",
				"customer": self.customer.name,
				"ro_unit": self.unit.name,
				"start_date": today(),
				"duration_months": 12,
				"amount": 3000,
				"visits_included": visits_included,
			}
		).insert()

	def test_activate_creates_scheduled_visits(self):
		contract = self._contract(visits_included=4)
		activate_contract(contract.name)
		visits = frappe.get_all(
			"Service Visit", filters={"contract": contract.name}, fields=["status", "visit_type"]
		)
		self.assertEqual(len(visits), 4)
		for v in visits:
			self.assertEqual(v.status, "Scheduled")
			self.assertEqual(v.visit_type, "Scheduled")  # existing select value, not a new one

	def test_activate_is_idempotent(self):
		contract = self._contract(visits_included=3)
		activate_contract(contract.name)
		count_1 = frappe.db.count("Service Visit", {"contract": contract.name})
		generate_scheduled_visits(frappe.get_doc("AMC Contract", contract.name))  # simulate a retried call
		count_2 = frappe.db.count("Service Visit", {"contract": contract.name})
		self.assertEqual(count_1, count_2)

	def test_activate_cannot_run_twice_through_the_api(self):
		contract = self._contract(visits_included=2)
		activate_contract(contract.name)
		with self.assertRaises(frappe.ValidationError):
			activate_contract(contract.name)

	def test_cancel_cancels_only_future_scheduled_visits(self):
		contract = self._contract(visits_included=3)
		activate_contract(contract.name)
		visit_names = frappe.get_all("Service Visit", filters={"contract": contract.name}, pluck="name")

		# Complete one, leave the rest Scheduled.
		completed = frappe.get_doc("Service Visit", visit_names[0])
		completed.status = "Completed"
		completed.no_parts_used = 1
		completed.save()

		cancel_contract(contract.name)

		completed.reload()
		self.assertEqual(completed.status, "Completed")  # untouched

		others = frappe.get_all(
			"Service Visit", filters={"contract": contract.name, "name": ("!=", completed.name)}, pluck="status"
		)
		self.assertTrue(all(s == "Cancelled" for s in others))

	def test_visits_used_counter_still_works_after_scheduling(self):
		contract = self._contract(visits_included=2)
		activate_contract(contract.name)
		visit = frappe.get_doc(
			"Service Visit", frappe.db.get_value("Service Visit", {"contract": contract.name}, "name")
		)
		visit.status = "Completed"
		visit.no_parts_used = 1
		visit.save()
		contract.reload()
		self.assertEqual(contract.visits_used, 1)
