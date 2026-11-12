import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, getdate

from amc_pilot.amcpilot.services.amc_contracts import activate_contract, cancel_contract
from amc_pilot.amcpilot.tests.utils import make_contract, make_customer, make_model, make_unit_simple


class TestAMCContract(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("ContractBrand", "C1", {"Contract Filter": 90})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876600001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing)
			if existing
			else make_customer("Contract Cust", "9876600001")
		)
		self.unit = make_unit_simple(self.customer.name, self.model.name)

	def test_end_date_computed(self):
		c = make_contract(self.unit.name, self.customer.name, start_date="2026-01-15", duration_months=12)
		self.assertEqual(getdate(c.end_date), getdate(add_months("2026-01-15", 12)))

	def test_new_contract_is_draft(self):
		c = make_contract(self.unit.name, self.customer.name)
		self.assertEqual(c.status, "Draft")
		self.assertEqual(c.visits_used, 0)

	def test_activate_then_second_active_blocked(self):
		c1 = make_contract(self.unit.name, self.customer.name)
		activate_contract(c1.name)
		c1.reload()
		self.assertEqual(c1.status, "Active")

		c2 = make_contract(self.unit.name, self.customer.name)
		with self.assertRaises(frappe.ValidationError):
			activate_contract(c2.name)

	def test_cancel_contract(self):
		c = make_contract(self.unit.name, self.customer.name)
		cancel_contract(c.name)
		c.reload()
		self.assertEqual(c.status, "Cancelled")
		with self.assertRaises(frappe.ValidationError):
			activate_contract(c.name)
