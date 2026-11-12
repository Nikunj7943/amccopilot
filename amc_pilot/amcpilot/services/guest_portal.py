"""The guest-facing QR page: /ro/<token>. No login. Shows only what the token's own
unit needs to show, and the one action a guest may take is requesting a visit.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import getdate, today


def get_unit_by_token(token: str):
	"""Look up the RO Unit for a QR token, or None. Never raises on a bad token."""
	if not token or not isinstance(token, str):
		return None
	name = frappe.db.get_value("RO Unit", {"qr_token": token}, "name")
	return frappe.get_doc("RO Unit", name) if name else None


def build_portal_context(unit) -> dict:
	customer_name = frappe.db.get_value("AMC Customer", unit.customer, "customer_name")
	model = frappe.db.get_value("RO Model", unit.ro_model, ["brand", "model_name", "ro_type"], as_dict=True)
	contract = frappe.db.get_value(
		"AMC Contract", {"ro_unit": unit.name, "status": "Active"}, ["name", "end_date"], as_dict=True
	)
	settings = frappe.get_single("AMC Settings")

	filters_due = []
	for row in unit.unit_filters:
		filters_due.append(
			{
				"part": row.service_part,
				"next_due_on": row.next_due_on,
				"overdue": bool(row.next_due_on and getdate(row.next_due_on) < getdate(today())),
			}
		)
	filters_due.sort(key=lambda r: (r["next_due_on"] is None, r["next_due_on"]))

	return {
		"customer_name": customer_name,
		"unit_name": unit.name,
		"brand": model.brand if model else "",
		"model_name": model.model_name if model else "",
		"ro_type": model.ro_type if model else "",
		"install_date": unit.install_date,
		"status": unit.status,
		"contract_active": bool(contract),
		"contract_end_date": contract.end_date if contract else None,
		"filters_due": filters_due,
		"business_name": settings.business_name,
		"owner_mobile": settings.owner_mobile,
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="token", limit=5, seconds=60 * 60)
def request_service(token: str) -> dict:
	"""A guest asks for a visit. Creates one Scheduled Service Visit. Rate limited per token."""
	unit = get_unit_by_token(token)
	if not unit:
		frappe.throw(_("Invalid QR code."))

	today_str = today()
	already = frappe.db.exists(
		"Service Visit", {"ro_unit": unit.name, "scheduled_date": today_str, "status": "Scheduled"}
	)
	if already:
		return {"status": "already_requested", "visit": already}

	visit = frappe.get_doc(
		{
			"doctype": "Service Visit",
			"ro_unit": unit.name,
			"visit_type": "Complaint",
			"status": "Scheduled",
			"scheduled_date": today_str,
			"notes": "Requested by the customer from the QR page.",
		}
	)
	visit.insert(ignore_permissions=True)
	return {"status": "requested", "visit": visit.name}
