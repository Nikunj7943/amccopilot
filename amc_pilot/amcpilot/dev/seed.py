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
			{"business_name": "Demo RO Care", "owner_name": "Demo Owner", "owner_mobile": "9825033001", "business_upi_id": "demorocare@upi"}
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

	_seed_contracts_and_visits(customers)

	frappe.db.commit()
	print("Demo data ready:", {dt: frappe.db.count(dt) for dt in (
		"Service Part", "RO Model", "AMC Customer", "RO Unit", "AMC Technician",
		"AMC Contract", "Service Visit")})


def _seed_contracts_and_visits(customers):
	from amc_pilot.amcpilot.services.amc_contracts import activate_contract

	# A customer whose AMC renewal is due in 7 days and whose filter is due tomorrow,
	# so the Reminders page always has something to show.
	due_customer = frappe.db.get_value("AMC Customer", {"mobile_no": "9825099001"})
	if not due_customer:
		due_customer = frappe.get_doc(
			{
				"doctype": "AMC Customer",
				"customer_name": "Due Soon Test",
				"mobile_no": "9825099001",
				"area": "Demo Area",
				"city": "Ahmedabad",
			}
		).insert().name
	model_name = frappe.db.get_value("RO Model", {"brand": "DemoPure", "model_name": "Aqua 7L"})
	if model_name and not frappe.db.exists("RO Unit", {"customer": due_customer}):
		unit = frappe.get_doc(
			{
				"doctype": "RO Unit",
				"customer": due_customer,
				"ro_model": model_name,
				"install_date": add_days(today(), -1),
			}
		).insert()
		contract = frappe.get_doc(
			{
				"doctype": "AMC Contract",
				"customer": due_customer,
				"ro_unit": unit.name,
				"start_date": add_days(today(), -358),
				"duration_months": 12,
				"amount": 2400,
				"visits_included": 2,
			}
		).insert()
		activate_contract(contract.name)
		frappe.db.set_value("AMC Contract", contract.name, "end_date", add_days(today(), 7))

	# Ramesh (first customer) gets an active, paid AMC contract with one completed visit.
	unit = frappe.db.get_value("RO Unit", {"customer": customers["9825011001"]}, "name")
	if unit and not frappe.db.exists("AMC Contract", {"ro_unit": unit}):
		contract = frappe.get_doc(
			{
				"doctype": "AMC Contract",
				"customer": customers["9825011001"],
				"ro_unit": unit,
				"start_date": add_days(today(), -300),
				"duration_months": 12,
				"amount": 2400,
				"visits_included": 2,
				"payment_status": "Paid",
			}
		).insert()
		activate_contract(contract.name)
		from amc_pilot.amcpilot.services.payments import create_payment, mark_paid_manually

		payment_name = create_payment(contract.name)
		mark_paid_manually(payment_name, method="UPI")

		tech = frappe.db.get_value("AMC Technician", {"technician_name": "Demo Technician One"})
		part = frappe.db.get_value("RO Unit Filter", {"parent": unit}, "service_part")
		visit = frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": unit,
				"contract": contract.name,
				"technician": tech,
				"visit_type": "Scheduled",
				"scheduled_date": add_days(today(), -60),
				"status": "Completed",
				"completed_on": add_days(today(), -60),
				"parts_used": [{"service_part": part, "qty": 1, "rate": 0}] if part else [],
			}
		).insert()

	# Priya (fifth customer) gets a draft contract, not yet activated, to show that state too.
	unit2 = frappe.db.get_value("RO Unit", {"customer": customers["9825011005"]}, "name")
	if unit2 and not frappe.db.exists("AMC Contract", {"ro_unit": unit2}):
		frappe.get_doc(
			{
				"doctype": "AMC Contract",
				"customer": customers["9825011005"],
				"ro_unit": unit2,
				"start_date": today(),
				"duration_months": 12,
				"amount": 2200,
				"visits_included": 2,
			}
		).insert()
