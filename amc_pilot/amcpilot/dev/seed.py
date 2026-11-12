"""Demo data for hand-testing and Playwright runs. Developer sites only.

Run:  bench --site amcpilot.localhost execute amc_pilot.amcpilot.dev.seed.run
Safe to run again: existing records are reused, nothing is duplicated.
Everything here is sample data, not defaults: no business logic lives in this file.
"""

import frappe
from frappe.utils import add_days, today

PARTS = [
	("Sediment Filter", "Filter", 250),
	("Carbon Filter", "Filter", 350),
	("Post Carbon Filter", "Filter", 300),
	("RO Membrane", "Membrane", 2200),
	("UV Lamp", "Other", 600),
	("Booster Pump", "Pump", 1800),
	("Inlet Adaptor", "Adaptor", 120),
]

MODELS = [
	# brand, model, ro_type, {part: interval_days}
	("DemoPure", "Aqua 7L", "RO+UV", {"Sediment Filter": 180, "Carbon Filter": 180, "Post Carbon Filter": 365}),
	("DemoPure", "Slim 5L", "RO", {"Sediment Filter": 150, "Post Carbon Filter": 365}),
	("CleanSip", "UVF Max", "RO+UV+UF", {"Sediment Filter": 120, "Carbon Filter": 240, "Post Carbon Filter": 540}),
]

CUSTOMERS = [
	("Ramesh Patel", "9825011001", "Navrangpura", "Ahmedabad", "380009", "Gujarati"),
	("Sunita Shah", "9825011002", "Satellite", "Ahmedabad", "380015", "Gujarati"),
	("Kiran Desai", "9825011003", "Adajan", "Surat", "395009", "Hindi"),
	("Mehul Joshi", "9825011004", "Alkapuri", "Vadodara", "390007", "English"),
	("Priya Mehta", "9825011005", "Vesu", "Surat", "395007", "Gujarati"),
]

# (customer mobile, "brand model", days ago installed or None)
UNITS = [
	("9825011001", "DemoPure Aqua 7L", 400),
	("9825011002", "DemoPure Slim 5L", 100),
	("9825011003", "CleanSip UVF Max", 30),
	("9825011004", "DemoPure Aqua 7L", None),
	("9825011005", "CleanSip UVF Max", 700),
]

TECHNICIANS = [("Demo Technician One", "9825022001"), ("Demo Technician Two", "9825022002")]


def run():
	if not frappe.conf.developer_mode:
		frappe.throw("Demo data can only be created on a developer-mode site.")

	settings = frappe.get_single("AMC Settings")
	if not settings.business_name:
		settings.update(
			{"business_name": "Demo RO Care", "owner_name": "Demo Owner", "owner_mobile": "9825033001"}
		)
		settings.save()

	for name, part_type, price in PARTS:
		if not frappe.db.exists("Service Part", name):
			frappe.get_doc(
				{"doctype": "Service Part", "part_name": name, "part_type": part_type, "default_price": price}
			).insert()

	for brand, model, ro_type, filters in MODELS:
		if not frappe.db.exists("RO Model", f"{brand} {model}"):
			frappe.get_doc(
				{
					"doctype": "RO Model",
					"brand": brand,
					"model_name": model,
					"ro_type": ro_type,
					"model_filters": [
						{"service_part": p, "change_interval_days": d} for p, d in filters.items()
					],
				}
			).insert()

	customers = {}
	for cname, mobile, area, city, pincode, lang in CUSTOMERS:
		existing = frappe.db.get_value("AMC Customer", {"mobile_no": mobile})
		if existing:
			customers[mobile] = existing
			continue
		doc = frappe.get_doc(
			{
				"doctype": "AMC Customer",
				"customer_name": cname,
				"mobile_no": mobile,
				"address": f"{area}, {city}",
				"area": area,
				"city": city,
				"pincode": pincode,
				"preferred_language": lang,
			}
		).insert()
		customers[mobile] = doc.name

	for mobile, model, days_ago in UNITS:
		customer = customers[mobile]
		if frappe.db.exists("RO Unit", {"customer": customer, "ro_model": model}):
			continue
		frappe.get_doc(
			{
				"doctype": "RO Unit",
				"customer": customer,
				"ro_model": model,
				"install_date": add_days(today(), -days_ago) if days_ago else None,
				"serial_no": f"DEMO-{mobile[-4:]}",
			}
		).insert()

	for tname, mobile in TECHNICIANS:
		if not frappe.db.exists("AMC Technician", {"technician_name": tname}):
			frappe.get_doc({"doctype": "AMC Technician", "technician_name": tname, "mobile_no": mobile}).insert()

	frappe.db.commit()
	print("Demo data ready:", {dt: frappe.db.count(dt) for dt in (
		"Service Part", "RO Model", "AMC Customer", "RO Unit", "AMC Technician")})
