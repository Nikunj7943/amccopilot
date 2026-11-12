"""Small factories shared by the tests."""

import frappe


def make_part(name: str, part_type: str = "Filter"):
	if frappe.db.exists("Service Part", name):
		return frappe.get_doc("Service Part", name)
	return frappe.get_doc({"doctype": "Service Part", "part_name": name, "part_type": part_type}).insert()


def make_model(brand: str, model: str, filters: dict | None = None):
	"""filters = {part_name: interval_days}"""
	name = f"{brand} {model}"
	if frappe.db.exists("RO Model", name):
		return frappe.get_doc("RO Model", name)
	rows = []
	for part_name, days in (filters or {}).items():
		make_part(part_name)
		rows.append({"service_part": part_name, "change_interval_days": days})
	return frappe.get_doc(
		{"doctype": "RO Model", "brand": brand, "model_name": model, "model_filters": rows}
	).insert()


def make_customer(name: str = "Test Customer", mobile: str = "9876543210", **kw):
	"""Insert a customer (tests that expect a duplicate error use frappe.get_doc directly)."""
	return frappe.get_doc(
		{"doctype": "AMC Customer", "customer_name": name, "mobile_no": mobile, **kw}
	).insert()


def make_user(email: str, role: str):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
			"roles": [{"role": role}],
		}
	)
	user.insert(ignore_permissions=True)
	return user
