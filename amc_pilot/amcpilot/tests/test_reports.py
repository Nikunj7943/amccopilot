import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.services.service_visits import create_filter_change_visit
from amc_pilot.amcpilot.tests.utils import make_customer, make_model, make_part


def make_unit(customer, model, **kw):
	return frappe.get_doc({"doctype": "RO Unit", "customer": customer, "ro_model": model, **kw}).insert()


class TestUnbilledAndUnpaidReport(IntegrationTestCase):
	def test_shows_completed_visit_with_outstanding_amount(self):
		from amc_pilot.amcpilot.report.unbilled_and_unpaid.unbilled_and_unpaid import execute

		model = make_model("ReportBrand", "RP1")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877400001"})
		customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Report Cust", "9877400001")
		)
		make_part("Report Part", "Other")
		unit = make_unit(customer.name, model.name)
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": unit.name,
				"scheduled_date": "2026-02-01",
				"status": "Completed",
				"no_parts_used": 1,
				"visit_charge": 300,
				"payment_collected": 100,
			}
		).insert()

		columns, data = execute()
		row = next((r for r in data if r["name"] == visit.name), None)
		self.assertIsNotNone(row)
		self.assertEqual(row["outstanding"], 200)

	def test_fully_paid_visit_excluded(self):
		from amc_pilot.amcpilot.report.unbilled_and_unpaid.unbilled_and_unpaid import execute

		model = make_model("ReportBrand2", "RP2")
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877400002"})
		customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Report Cust 2", "9877400002")
		)
		unit = make_unit(customer.name, model.name)
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": unit.name,
				"scheduled_date": "2026-02-01",
				"status": "Completed",
				"no_parts_used": 1,
				"visit_charge": 300,
				"payment_collected": 300,
			}
		).insert()

		_, data = execute()
		self.assertNotIn(visit.name, [r["name"] for r in data])


class TestPartsDueReport(IntegrationTestCase):
	def test_shows_filters_within_window_and_creates_visit(self):
		from amc_pilot.amcpilot.report.parts_due.parts_due import execute

		model = make_model("ReportBrand3", "RP3", {"Report Filter": 10})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9877400003"})
		customer = (
			frappe.get_doc("AMC Customer", existing) if existing else make_customer("Report Cust 3", "9877400003")
		)
		unit = make_unit(customer.name, model.name, install_date=frappe.utils.add_days(frappe.utils.today(), -5))

		_, data = execute({"days": 15})
		row = next((r for r in data if r["ro_unit"] == unit.name), None)
		self.assertIsNotNone(row)

		visit_name = create_filter_change_visit(unit.name, row["service_part"])
		visit = frappe.get_doc("Service Visit", visit_name)
		self.assertEqual(visit.parts_used[0].service_part, row["service_part"])
