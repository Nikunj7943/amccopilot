import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days

from amc_pilot.amcpilot.services.dashboard import overdue_filters_count
from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_unit_simple


class TestDashboard(IntegrationTestCase):
	def test_overdue_filters_count_only_active_units(self):
		model = make_model("DashBrand", "D1", {"Dash Filter": 10})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876999001"})
		customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Dash Cust", "9876999001")
		)
		before = overdue_filters_count()

		# install_date 30 days ago + 10 day interval => clearly overdue
		make_unit_simple(customer.name, model.name, install_date=add_days(frappe.utils.today(), -30))
		self.assertEqual(overdue_filters_count(), before + 1)

		inactive_model = make_model("DashBrand2", "D2", {"Dash Filter 2": 10})
		make_unit_simple(
			customer.name, inactive_model.name, install_date=add_days(frappe.utils.today(), -30), status="Inactive"
		)
		# inactive unit's overdue filter must not be counted
		self.assertEqual(overdue_filters_count(), before + 1)
