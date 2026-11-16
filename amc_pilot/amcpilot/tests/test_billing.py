import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.amc_contracts import activate_contract
from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_part, make_user


def make_plan(name, coverage, **kw):
	if frappe.db.exists("AMC Plan", name):
		return frappe.get_doc("AMC Plan", name)
	return frappe.get_doc(
		{"doctype": "AMC Plan", "plan_name": name, "coverage": coverage, "visits_per_year": 4, **kw}
	).insert()


def make_covered_contract(unit, customer, plan_name, visits_included=5):
	c = frappe.get_doc(
		{
			"doctype": "AMC Contract",
			"customer": customer,
			"ro_unit": unit,
			"plan": plan_name,
			"start_date": "2026-01-01",
			"duration_months": 12,
			"amount": 3000,
			"visits_included": visits_included,
		}
	).insert()
	activate_contract(c.name)
	c.reload()
	return c


def make_visit(unit, contract=None, parts=None):
	return frappe.get_doc(
		{
			"doctype": "Service Visit",
			"ro_unit": unit,
			"contract": contract,
			"scheduled_date": "2026-02-01",
			"visit_charge": None,
			"parts_used": parts or [],
		}
	).insert()


class TestBillingCoverage(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("BillBrand", "B1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877000001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Bill Cust", "9877000001")
		)
		make_part("Bill Filter Part", "Filter")
		make_part("Bill Pump Part", "Pump")
		settings = frappe.get_single("AMC Settings")
		settings.default_visit_charge = 150
		settings.save()

	def _unit(self):
		return frappe.get_doc({"doctype": "RO Unit", "customer": self.customer.name, "ro_model": self.model.name}).insert()

	def _parts(self):
		return [
			{"service_part": "Bill Filter Part", "qty": 1, "rate": 200},
			{"service_part": "Bill Pump Part", "qty": 1, "rate": 500},
		]

	def test_labour_only_coverage(self):
		plan = make_plan("Labour Only Plan", "Labour Only")
		unit = self._unit()
		contract = make_covered_contract(unit.name, self.customer.name, plan.name)
		visit = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(visit.visit_charge, 0)
		rows = {r.service_part: r.chargeable for r in visit.parts_used}
		self.assertEqual(rows["Bill Filter Part"], 200)  # filter still chargeable
		self.assertEqual(rows["Bill Pump Part"], 500)
		self.assertEqual(visit.total_chargeable, 700)

	def test_labour_plus_filters_coverage(self):
		plan = make_plan("Labour Filters Plan", "Labour + Filters")
		unit = self._unit()
		contract = make_covered_contract(unit.name, self.customer.name, plan.name)
		visit = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(visit.visit_charge, 0)
		rows = {r.service_part: r.chargeable for r in visit.parts_used}
		self.assertEqual(rows["Bill Filter Part"], 0)  # filter free
		self.assertEqual(rows["Bill Pump Part"], 500)  # non-filter chargeable
		self.assertEqual(visit.total_chargeable, 500)

	def test_comprehensive_coverage(self):
		plan = make_plan("Comprehensive Plan", "Comprehensive")
		unit = self._unit()
		contract = make_covered_contract(unit.name, self.customer.name, plan.name)
		visit = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(visit.visit_charge, 0)
		for row in visit.parts_used:
			self.assertEqual(row.chargeable, 0)
		self.assertEqual(visit.total_chargeable, 0)

	def test_no_contract_charges_everything(self):
		unit = self._unit()
		visit = make_visit(unit.name, None, self._parts())
		self.assertEqual(visit.visit_charge, 150)  # AMC Settings.default_visit_charge
		self.assertEqual(visit.total_chargeable, 150 + 200 + 500)
		self.assertEqual(visit.covered_by_contract, 0)

	def test_cancelled_contract_charges_everything(self):
		plan = make_plan("To Cancel Plan", "Comprehensive")
		unit = self._unit()
		contract = make_covered_contract(unit.name, self.customer.name, plan.name)
		from amc_pilot.amcpilot.services.amc_contracts import cancel_contract

		cancel_contract(contract.name)
		visit = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(visit.visit_charge, 150)
		self.assertEqual(visit.total_chargeable, 150 + 200 + 500)

	def test_visits_included_cap_stops_coverage(self):
		plan = make_plan("Capped Plan", "Comprehensive")
		unit = self._unit()
		contract = make_covered_contract(unit.name, self.customer.name, plan.name, visits_included=1)
		v1 = make_visit(unit.name, contract.name, self._parts())
		v1.status = "Completed"
		v1.save()  # uses up the only included visit
		contract.reload()
		self.assertEqual(contract.visits_used, 1)

		v2 = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(v2.covered_by_contract, 0)
		self.assertEqual(v2.total_chargeable, 150 + 200 + 500)

	def test_legacy_contract_with_no_plan_stays_free_like_before(self):
		"""Active contract created before AMC Plan existed: no plan link yet.
		Must behave exactly as before this stage (Rs.0 while covered)."""
		unit = self._unit()
		contract = frappe.get_doc(
			{
				"doctype": "AMC Contract",
				"customer": self.customer.name,
				"ro_unit": unit.name,
				"start_date": "2026-01-01",
				"duration_months": 12,
				"amount": 3000,
				"visits_included": 2,
			}
		).insert()
		activate_contract(contract.name)
		visit = make_visit(unit.name, contract.name, self._parts())
		self.assertEqual(visit.visit_charge, 0)
		self.assertEqual(visit.total_chargeable, 0)
