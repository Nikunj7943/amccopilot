import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from amc_pilot.amcpilot.services.amc_contracts import activate_contract
from amc_pilot.amcpilot.services.reminders import (
	build_filter_due_message,
	build_renewal_message,
	get_filter_due_reminders,
	get_renewal_reminders,
	whatsapp_link,
)
from amc_pilot.amcpilot.tests.utils import make_contract, make_customer, make_model, make_unit_simple


class TestReminders(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("RemindBrand", "R1", {"Remind Filter": 30})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876700001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing)
			if existing
			else make_customer("Remind Cust", "9876700001")
		)

	def test_default_templates_exist(self):
		for t in ("Renewal Reminder", "Filter Due Reminder", "Visit Reminder", "Payment Receipt"):
			self.assertTrue(frappe.db.exists("Message Template", {"template_type": t, "language": "English"}))

	def test_whatsapp_link_format(self):
		link = whatsapp_link("9876543210", "Hello")
		self.assertEqual(link, "https://wa.me/919876543210?text=Hello")
		self.assertEqual(whatsapp_link("+91 98765 43210", "Hi"), "https://wa.me/919876543210?text=Hi")

	def test_renewal_reminder_found_on_configured_day(self):
		unit = make_unit_simple(self.customer.name, self.model.name)
		contract = make_contract(unit.name, self.customer.name, end_date=None, start_date=add_days(today(), -365 + 7))
		activate_contract(contract.name)
		contract.reload()
		# End date lands ~7 days out, which is in the default "30,15,7,0" list.
		found = [c for c in get_renewal_reminders() if c["name"] == contract.name]
		self.assertEqual(len(found), 1)
		self.assertEqual(found[0]["days_left"], 7)

		msg = build_renewal_message(found[0])
		self.assertIn("Remind Cust", msg["message"])
		self.assertIn("wa.me/919876700001", msg["link"])

	def test_filter_due_reminder(self):
		unit = make_unit_simple(self.customer.name, self.model.name, install_date=add_days(today(), -29))
		rows = [r for r in get_filter_due_reminders() if r["ro_unit"] == unit.name]
		self.assertEqual(len(rows), 1)
		msg = build_filter_due_message(rows[0])
		self.assertIn("Remind Filter", msg["message"])
		self.assertTrue(msg["link"].startswith("https://wa.me/"))

	def test_inactive_unit_excluded_from_filter_reminders(self):
		unit = make_unit_simple(self.customer.name, self.model.name, install_date=add_days(today(), -29), status="Inactive")
		rows = [r for r in get_filter_due_reminders() if r["ro_unit"] == unit.name]
		self.assertEqual(len(rows), 0)
