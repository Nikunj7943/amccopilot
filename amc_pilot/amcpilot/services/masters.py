"""Rules for the master DocTypes: Service Part, RO Model."""

import frappe
from frappe import _


def is_filter_type(part_type: str | None) -> int:
	"""A Service Part is a filter exactly when its type is 'Filter'."""
	return 1 if part_type == "Filter" else 0


def validate_filter_rows(rows, row_label: str = "Filter") -> None:
	"""Check child rows that have `service_part` and `change_interval_days`.

	Every part must be a filter, every interval must be > 0, and a part may appear once.
	"""
	seen = set()
	for row in rows:
		if not row.service_part:
			continue
		if row.service_part in seen:
			frappe.throw(
				_("Row {0}: {1} is added more than once.").format(row.idx, frappe.bold(row.service_part))
			)
		seen.add(row.service_part)

		if not frappe.db.get_value("Service Part", row.service_part, "is_filter"):
			frappe.throw(
				_("Row {0}: {1} is not a filter. Only Service Parts of type Filter can be added here.").format(
					row.idx, frappe.bold(row.service_part)
				)
			)
		if (row.change_interval_days or 0) <= 0:
			frappe.throw(_("Row {0}: Change Interval (days) must be greater than 0.").format(row.idx))


def validate_unique_ro_model(doc) -> None:
	"""(brand, model_name) must be unique. Whitespace is trimmed first."""
	doc.brand = (doc.brand or "").strip()
	doc.model_name = (doc.model_name or "").strip()

	duplicate = frappe.db.get_value(
		"RO Model",
		{"brand": doc.brand, "model_name": doc.model_name, "name": ("!=", doc.name or "")},
		"name",
	)
	if duplicate:
		frappe.throw(
			_("RO Model {0} already exists for brand {1}.").format(
				frappe.bold(doc.model_name), frappe.bold(doc.brand)
			),
			exc=frappe.DuplicateEntryError,
		)
