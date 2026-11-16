"""Service Visit rules: contract linking, charge totals, and completing a visit."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today


def find_active_contract(ro_unit: str) -> str | None:
	return frappe.db.get_value("AMC Contract", {"ro_unit": ro_unit, "status": "Active"}, "name")


def validate_tds(doc) -> None:
	if doc.status != "Completed":
		return
	if frappe.db.get_single_value("AMC Settings", "require_tds_on_visit") and (
		doc.tds_before is None or doc.tds_after is None
	):
		frappe.throw(_("TDS Before and TDS After are required to complete this visit."))


def validate_parts_rule(doc) -> None:
	"""A visit cannot be marked Completed with an empty Parts Used table unless
	'No Parts Used' is ticked. Runs in validate(), so every path (form, API,
	import, another script) goes through it."""
	if doc.status != "Completed":
		return
	if not doc.parts_used and not doc.no_parts_used:
		frappe.throw(
			_("Add at least one row to Parts Used, or tick 'No Parts Used', before completing this visit.")
		)


def prepare_for_save(doc) -> None:
	from amc_pilot.amcpilot.services.billing import compute_charges
	from amc_pilot.amcpilot.services.permissions import enforce_technician_isolation

	enforce_technician_isolation(doc)
	if doc.is_new() and not doc.contract:
		doc.contract = find_active_contract(doc.ro_unit)
	compute_charges(doc)
	validate_tds(doc)
	validate_parts_rule(doc)


def update_unit_filters_after_visit(doc) -> None:
	"""On completion, parts used that are filters push their Last Changed On forward."""
	filter_parts = {
		row.service_part
		for row in doc.parts_used
		if frappe.db.get_value("Service Part", row.service_part, "is_filter")
	}
	if not filter_parts:
		return

	unit = frappe.get_doc("RO Unit", doc.ro_unit)
	changed_on = getdate(doc.completed_on or today())
	existing = {row.service_part for row in unit.unit_filters}
	for part in filter_parts:
		if part in existing:
			for row in unit.unit_filters:
				if row.service_part == part:
					row.last_changed_on = changed_on
		else:
			interval = frappe.db.get_value(
				"RO Model Filter",
				{"parent": unit.ro_model, "service_part": part},
				"change_interval_days",
			)
			unit.append(
				"unit_filters",
				{"service_part": part, "change_interval_days": interval or 180, "last_changed_on": changed_on},
			)
	unit.save(ignore_permissions=True)


def on_update(doc, method=None) -> None:
	"""Controller hook: runs after the document is saved (validate already ran)."""
	if doc.status != "Completed":
		return
	if not doc.completed_on:
		frappe.db.set_value("Service Visit", doc.name, "completed_on", now_datetime(), update_modified=False)
		doc.completed_on = now_datetime()
	update_unit_filters_after_visit(doc)
	if doc.contract:
		from amc_pilot.amcpilot.services.amc_contracts import recompute_visits_used

		recompute_visits_used(doc.contract)


@frappe.whitelist()
def create_filter_change_visit(ro_unit: str, service_part: str) -> str:
	"""Used by the Parts Due report's row action: schedule a visit to change one
	overdue/soon-due filter today, with that part pre-filled in Parts Used."""
	frappe.has_permission("Service Visit", "create", throw=True)
	frappe.has_permission("RO Unit", "read", doc=ro_unit, throw=True)

	rate = frappe.db.get_value("Service Part", service_part, "default_price") or 0
	visit = frappe.get_doc(
		{
			"doctype": "Service Visit",
			"ro_unit": ro_unit,
			"visit_type": "Scheduled",
			"status": "Scheduled",
			"scheduled_date": today(),
			"notes": _("Filter change: {0}").format(service_part),
			"parts_used": [{"service_part": service_part, "qty": 1, "rate": rate}],
		}
	)
	visit.insert()
	return visit.name
