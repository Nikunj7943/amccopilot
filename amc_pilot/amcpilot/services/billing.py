"""The one place visit charges are computed. See AMC Plan for the coverage types.

Rule: an Active contract, while its Visits Included have not run out, gives
coverage according to its plan:
  - Labour Only      : labour free, every part chargeable.
  - Labour + Filters  : labour free, Service Parts with is_filter=1 free, others chargeable.
  - Comprehensive     : labour and every part free.
An Active contract with no plan is treated as Comprehensive (this is the pre-G2
behaviour for existing contracts; see the migration patch that assigns them a
real plan). No contract, an inactive/expired/cancelled one, or one whose
included visits are used up: labour is AMC Settings.default_visit_charge and
every part is chargeable at rate x qty.
"""

import frappe
from frappe.utils import flt


def _active_contract_with_room(contract_name: str | None) -> dict | None:
	if not contract_name:
		return None
	contract = frappe.db.get_value(
		"AMC Contract",
		contract_name,
		["status", "plan", "visits_included", "visits_used"],
		as_dict=True,
	)
	if not contract or contract.status != "Active":
		return None
	if contract.visits_used >= contract.visits_included:
		return None
	return contract


def _coverage_of(contract: dict) -> str:
	if not contract.plan:
		return "Comprehensive"  # legacy contract with no plan yet: keep today's zero-charge behaviour
	return frappe.db.get_value("AMC Plan", contract.plan, "coverage") or "Comprehensive"


def compute_charges(doc) -> None:
	"""Fill doc.parts_used[].chargeable, doc.total_chargeable and doc.covered_by_contract.

	Also keeps the older visit_charge/total_amount fields in step, so nothing
	that already reads them breaks.
	"""
	contract = _active_contract_with_room(doc.contract)
	coverage = _coverage_of(contract) if contract else None
	doc.covered_by_contract = 1 if contract else 0

	labour_free = coverage in ("Labour Only", "Labour + Filters", "Comprehensive")
	parts_free_if_filter = coverage == "Labour + Filters"
	parts_all_free = coverage == "Comprehensive"

	if labour_free:
		doc.visit_charge = 0
	elif doc.visit_charge is None:
		doc.visit_charge = frappe.db.get_single_value("AMC Settings", "default_visit_charge") or 0

	parts_total_chargeable = 0
	for row in doc.parts_used:
		amount = flt(row.qty) * flt(row.rate)
		row.amount = amount

		if parts_all_free:
			row.chargeable = 0
		elif parts_free_if_filter and frappe.db.get_value("Service Part", row.service_part, "is_filter"):
			row.chargeable = 0
		else:
			row.chargeable = amount
		parts_total_chargeable += flt(row.chargeable)

	doc.total_chargeable = flt(doc.visit_charge) + parts_total_chargeable
	doc.total_amount = doc.total_chargeable  # kept for anything still reading the old field
