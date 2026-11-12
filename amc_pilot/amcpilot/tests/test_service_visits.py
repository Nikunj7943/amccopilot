import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from amc_pilot.amcpilot.services.amc_contracts import activate_contract
from amc_pilot.amcpilot.tests.utils import (
	make_contract,
	make_customer,
	make_model,
	make_part,
	make_unit_simple,
)


def make_visit(unit, **kw):
	return frappe.get_doc({"doctype": "Service Visit", "ro_unit": unit, "scheduled_date": today(), **kw}).insert()


class TestServiceVisit(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("VisitBrand", "V1", {"Visit Filter": 90})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876600002"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing)
			if existing
			else make_customer("Visit Cust", "9876600002")
		)
		self.unit = make_unit_simple(self.customer.name, self.model.name, install_date="2026-01-01")

	def test_active_contract_auto_linked(self):
		c = make_contract(self.unit.name, self.customer.name)
		activate_contract(c.name)
		visit = make_visit(self.unit.name)
		self.assertEqual(visit.contract, c.name)
		self.assertEqual(visit.covered_by_contract, 1)
		self.assertEqual(visit.visit_charge, 0)

	def test_no_contract_uses_default_charge(self):
		settings = frappe.get_single("AMC Settings")
		settings.default_visit_charge = 199
		settings.save()
		visit = make_visit(self.unit.name)
		self.assertEqual(visit.covered_by_contract, 0)
		self.assertEqual(visit.visit_charge, 199)

	def test_parts_total_and_amount(self):
		make_part("Visit Part X", "Other")
		visit = make_visit(
			self.unit.name,
			visit_charge=100,
			parts_used=[{"service_part": "Visit Part X", "qty": 2, "rate": 50}],
		)
		self.assertEqual(visit.parts_used[0].amount, 100)
		self.assertEqual(visit.total_amount, 200)

	def test_completing_visit_updates_filter_and_contract(self):
		c = make_contract(self.unit.name, self.customer.name)
		activate_contract(c.name)
		visit = make_visit(self.unit.name, parts_used=[{"service_part": "Visit Filter", "qty": 1, "rate": 0}])
		visit.status = "Completed"
		visit.save()

		row = next(r for r in frappe.get_doc("RO Unit", self.unit.name).unit_filters if r.service_part == "Visit Filter")
		self.assertTrue(row.last_changed_on)
		self.assertTrue(row.next_due_on)

		c.reload()
		self.assertEqual(c.visits_used, 1)

	def test_tds_required_when_setting_on(self):
		settings = frappe.get_single("AMC Settings")
		settings.require_tds_on_visit = 1
		settings.save()
		try:
			visit = make_visit(self.unit.name)
			visit.status = "Completed"
			with self.assertRaises(frappe.ValidationError):
				visit.save()
		finally:
			settings.require_tds_on_visit = 0
			settings.save()

	def test_technician_can_write_visit_but_not_contract(self):
		from amc_pilot.amcpilot.tests.utils import make_user

		tech = make_user("visit.tech@example.com", "AMC Technician").name
		self.assertTrue(frappe.has_permission("Service Visit", "write", user=tech))
		self.assertFalse(frappe.has_permission("AMC Contract", "write", user=tech))
