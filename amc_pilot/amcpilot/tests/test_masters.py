import frappe
from frappe.tests import IntegrationTestCase

from amc_pilot.amcpilot.tests.utils import make_model, make_part


class TestServicePart(IntegrationTestCase):
	def test_is_filter_derived_from_type(self):
		self.assertEqual(make_part("Sediment", "Filter").is_filter, 1)
		pump = make_part("Booster", "Pump")
		self.assertEqual(pump.is_filter, 0)
		pump.part_type = "Filter"
		pump.save()
		self.assertEqual(pump.is_filter, 1)

	def test_part_name_unique(self):
		make_part("Dup Part")
		with self.assertRaises(frappe.DuplicateEntryError):  # name == part_name, so the key clashes
			frappe.get_doc({"doctype": "Service Part", "part_name": "Dup Part", "part_type": "Other"}).insert()


class TestROModel(IntegrationTestCase):
	def test_name_is_brand_and_model(self):
		self.assertEqual(make_model("BrandX", "M1").name, "BrandX M1")

	def test_brand_model_unique(self):
		make_model("BrandY", "M1")
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc({"doctype": "RO Model", "brand": "BrandY", "model_name": "M1"}).insert()

	def test_same_model_name_other_brand_ok(self):
		make_model("BrandA", "Same")
		make_model("BrandB", "Same")

	def test_only_filters_allowed(self):
		make_part("Some Pump", "Pump")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "RO Model",
					"brand": "BrandZ",
					"model_name": "M1",
					"model_filters": [{"service_part": "Some Pump", "change_interval_days": 90}],
				}
			).insert()

	def test_interval_must_be_positive(self):
		make_part("Pos Filter")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "RO Model",
					"brand": "BrandZ",
					"model_name": "M2",
					"model_filters": [{"service_part": "Pos Filter", "change_interval_days": 0}],
				}
			).insert()
