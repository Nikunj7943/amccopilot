"""Service Visit rules: contract linking, charge totals, and completing a visit."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today


def find_active_contract(ro_unit: str) -> str | None:
	return frappe.db.get_value("AMC Contract", {"ro_unit": ro_unit, "status": "Active"}, "name")


def compute_amounts(doc) -> None:
	for row in doc.parts_used:
		row.amount = flt(row.qty) * flt(row.rate)

	doc.covered_by_contract = 0
	if doc.contract:
		contract = frappe.db.get_value(
			"AMC Contract", doc.contract, ["status", "visits_included", "visits_used"], as_dict=True
		)
		if contract and contract.status == "Active" and contract.visits_used < contract.visits_included:
			doc.covered_by_contract = 1

	if doc.covered_by_contract:
		doc.visit_charge = 0
	elif doc.visit_charge is None:
		doc.visit_charge = frappe.db.get_single_value("AMC Settings", "default_visit_charge") or 0

	parts_total = sum(flt(row.amount) for row in doc.parts_used)
	doc.total_amount = flt(doc.visit_charge) + parts_total


def validate_tds(doc) -> None:
	if doc.status != "Completed":
		return
	if frappe.db.get_single_value("AMC Settings", "require_tds_on_visit") and (
		doc.tds_before is None or doc.tds_after is None
	):
		frappe.throw(_("TDS Before and TDS After are required to complete this visit."))


def prepare_for_save(doc) -> None:
	if doc.is_new() and not doc.contract:
		doc.contract = find_active_contract(doc.ro_unit)
	compute_amounts(doc)
	validate_tds(doc)


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
