"""RO Unit rules: QR token, filter fill/reload, next due dates."""

import secrets

import frappe
from frappe import _
from frappe.utils import add_days, getdate


def ensure_qr_token(doc) -> None:
	"""Generate the QR token once.

	New document: always a fresh token (a copy never inherits the original's token).
	Saved document: the stored token is restored, so it can never change.
	"""
	if doc.is_new():
		doc.qr_token = secrets.token_urlsafe(16)
		return

	stored = frappe.db.get_value("RO Unit", doc.name, "qr_token")
	doc.qr_token = stored or secrets.token_urlsafe(16)


def set_title(doc) -> None:
	customer_name = doc.customer_name or (
		frappe.db.get_value("AMC Customer", doc.customer, "customer_name") if doc.customer else ""
	)
	doc.unit_title = f"{customer_name} - {doc.ro_model}".strip(" -")


def compute_next_due(doc) -> None:
	"""next_due_on = last_changed_on + change_interval_days; empty if either is missing."""
	for row in doc.unit_filters:
		if row.last_changed_on and (row.change_interval_days or 0) > 0:
			row.next_due_on = add_days(getdate(row.last_changed_on), row.change_interval_days)
		else:
			row.next_due_on = None


def add_missing_filters(doc) -> int:
	"""Append the RO Model's filters that the unit does not have yet. Returns rows added.

	Existing rows (and their dates and intervals) are never touched. New rows start with
	last_changed_on = install_date; if install_date is empty the date stays empty.
	"""
	if not doc.ro_model:
		return 0

	existing = {row.service_part for row in doc.unit_filters}
	model_filters = frappe.get_all(
		"RO Model Filter",
		filters={"parent": doc.ro_model, "parenttype": "RO Model"},
		fields=["service_part", "change_interval_days"],
		order_by="idx asc",
	)

	added = 0
	for model_filter in model_filters:
		if model_filter.service_part in existing:
			continue
		doc.append(
			"unit_filters",
			{
				"service_part": model_filter.service_part,
				"change_interval_days": model_filter.change_interval_days,
				"last_changed_on": doc.install_date or None,
			},
		)
		added += 1
	return added


def fill_filters_on_first_save(doc) -> None:
	"""On the first save of a unit with no filter rows, fill them from the RO Model."""
	if not doc.is_new() or doc.unit_filters:
		return
	if add_missing_filters(doc) and not doc.install_date:
		frappe.msgprint(
			_("Install Date is empty, so Last Changed On and Next Due On are left empty for the filters."),
			indicator="orange",
		)


def prepare_for_save(doc) -> None:
	"""Single entry point called by the RO Unit controller's validate()."""
	from amc_pilot.amcpilot.services.masters import validate_filter_rows

	ensure_qr_token(doc)
	set_title(doc)
	fill_filters_on_first_save(doc)
	validate_filter_rows(doc.unit_filters)
	compute_next_due(doc)


@frappe.whitelist()
def reload_filters_from_model(ro_unit: str) -> int:
	"""Add filters from the RO Model that the unit is missing. Never overwrites existing rows."""
	if not ro_unit or not isinstance(ro_unit, str):
		frappe.throw(_("RO Unit is required."))

	frappe.has_permission("RO Unit", "write", doc=ro_unit, throw=True)

	doc = frappe.get_doc("RO Unit", ro_unit)
	added = add_missing_filters(doc)
	if added:
		doc.save()
	return added
