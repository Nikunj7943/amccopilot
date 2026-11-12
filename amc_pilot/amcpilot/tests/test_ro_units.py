import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from amc_pilot.amcpilot.services.ro_units import reload_filters_from_model
from amc_pilot.amcpilot.tests.utils import make_customer, make_model


def make_unit(customer, model, **kw):
	return frappe.get_doc({"doctype": "RO Unit", "customer": customer.name, "ro_model": model.name, **kw}).insert()


class TestROUnit(IntegrationTestCase):
	def setUp(self):
		self.model = make_model("UnitBrand", "U1", {"U Sediment": 90, "U Carbon": 180})
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": "9876500001"})
		self.customer = (
			frappe.get_doc("AMC Customer", existing)
			if existing
			else make_customer("Unit Cust", "9876500001", address="12 Test Road", area="Test Area")
		)

	def test_filters_autofilled_with_install_date_and_next_due(self):
		unit = make_unit(self.customer, self.model, install_date="2026-01-10")
		rows = {r.service_part: r for r in unit.unit_filters}
		self.assertEqual(set(rows), {"U Sediment", "U Carbon"})
		self.assertEqual(getdate(rows["U Sediment"].last_changed_on), getdate("2026-01-10"))
		self.assertEqual(getdate(rows["U Sediment"].next_due_on), getdate(add_days("2026-01-10", 90)))
		self.assertEqual(getdate(rows["U Carbon"].next_due_on), getdate(add_days("2026-01-10", 180)))

	def test_empty_install_date_leaves_dates_empty(self):
		unit = make_unit(self.customer, self.model)
		self.assertEqual(len(unit.unit_filters), 2)
		for row in unit.unit_filters:
			self.assertFalse(row.last_changed_on)
			self.assertFalse(row.next_due_on)

	def test_next_due_recomputed_on_save(self):
		unit = make_unit(self.customer, self.model, install_date="2026-01-10")
		unit.unit_filters[0].last_changed_on = "2026-03-01"
		unit.unit_filters[0].change_interval_days = 30
		unit.save()
		self.assertEqual(getdate(unit.unit_filters[0].next_due_on), getdate(add_days("2026-03-01", 30)))

	def test_address_and_area_default_from_customer_but_editable(self):
		unit = make_unit(self.customer, self.model)
		self.assertEqual(unit.install_address, "12 Test Road")
		self.assertEqual(unit.area, "Test Area")
		other = make_unit(self.customer, self.model, install_address="Elsewhere", area="Other Area")
		self.assertEqual(other.install_address, "Elsewhere")
		self.assertEqual(other.area, "Other Area")

	def test_reload_adds_only_missing_and_never_overwrites(self):
		unit = make_unit(self.customer, self.model, install_date="2026-01-10")
		unit.unit_filters[0].last_changed_on = "2026-02-02"
		unit.unit_filters[0].change_interval_days = 45
		unit.save()
		kept = (unit.unit_filters[0].service_part, unit.unit_filters[0].last_changed_on)

		# Nothing missing: nothing changes.
		self.assertEqual(reload_filters_from_model(unit.name), 0)

		# Add a new filter to the model and drop one row from the unit.
		unit.reload()
		removed = unit.unit_filters[1].service_part
		unit.remove(unit.unit_filters[1])
		unit.save()

		self.assertEqual(reload_filters_from_model(unit.name), 1)
		unit.reload()
		rows = {r.service_part: r for r in unit.unit_filters}
		self.assertIn(removed, rows)
		self.assertEqual(getdate(rows[kept[0]].last_changed_on), getdate(kept[1]))  # untouched
		self.assertEqual(rows[kept[0]].change_interval_days, 45)  # untouched
		self.assertEqual(len(unit.unit_filters), 2)

	def test_qr_token_generated_once_and_unchanged(self):
		unit = make_unit(self.customer, self.model)
		token = unit.qr_token
		self.assertTrue(token)
		self.assertGreaterEqual(len(token), 20)
		unit.notes = "changed"
		unit.save()
		unit.reload()
		self.assertEqual(unit.qr_token, token)

		# tampering with the read-only field is ignored
		unit.qr_token = "hacked"
		unit.save()
		unit.reload()
		self.assertEqual(unit.qr_token, token)

	def test_duplicate_gets_its_own_token_and_original_is_unchanged(self):
		unit = make_unit(self.customer, self.model)
		token = unit.qr_token
		copy = frappe.copy_doc(unit)
		copy.insert()
		self.assertNotEqual(copy.qr_token, token)
		self.assertTrue(copy.qr_token)
		self.assertEqual(frappe.db.get_value("RO Unit", unit.name, "qr_token"), token)

	def test_title_shows_customer_and_model(self):
		unit = make_unit(self.customer, self.model)
		self.assertEqual(unit.unit_title, "Unit Cust - UnitBrand U1")
		self.assertTrue(unit.name.startswith("RO-"))
