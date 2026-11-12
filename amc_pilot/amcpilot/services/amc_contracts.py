"""AMC Contract rules: term dates, visit counting, activate/cancel actions."""

import frappe
from frappe import _
from frappe.utils import add_months, getdate, today


def compute_end_date(doc) -> None:
	if doc.start_date and doc.duration_months:
		doc.end_date = add_months(getdate(doc.start_date), int(doc.duration_months))


def recompute_visits_used(contract_name: str) -> int:
	count = frappe.db.count("Service Visit", {"contract": contract_name, "status": "Completed"})
	frappe.db.set_value("AMC Contract", contract_name, "visits_used", count, update_modified=False)
	return count


def prepare_for_save(doc) -> None:
	compute_end_date(doc)
	if doc.is_new():
		doc.status = "Draft"
		doc.visits_used = 0


@frappe.whitelist()
def activate_contract(contract: str) -> str:
	"""Mark a Draft contract Active. Refuses a second Active contract on the same unit."""
	frappe.has_permission("AMC Contract", "write", doc=contract, throw=True)
	doc = frappe.get_doc("AMC Contract", contract)
	if doc.status != "Draft":
		frappe.throw(_("Only a Draft contract can be activated."))

	clash = frappe.db.get_value(
		"AMC Contract", {"ro_unit": doc.ro_unit, "status": "Active", "name": ("!=", doc.name)}, "name"
	)
	if clash:
		frappe.throw(
			_("RO Unit {0} already has an active contract: {1}.").format(
				frappe.bold(doc.ro_unit), frappe.bold(clash)
			)
		)

	doc.status = "Active"
	doc.save()
	return doc.status


@frappe.whitelist()
def cancel_contract(contract: str) -> str:
	frappe.has_permission("AMC Contract", "write", doc=contract, throw=True)
	doc = frappe.get_doc("AMC Contract", contract)
	if doc.status not in ("Draft", "Active"):
		frappe.throw(_("Only a Draft or Active contract can be cancelled."))
	doc.status = "Cancelled"
	doc.save()
	return doc.status


def expire_overdue_contracts() -> int:
	"""Daily job: Active contracts whose end_date has passed become Expired."""
	names = frappe.get_all(
		"AMC Contract", filters={"status": "Active", "end_date": ("<", today())}, pluck="name"
	)
	for name in names:
		frappe.db.set_value("AMC Contract", name, "status", "Expired")
	if names:
		frappe.db.commit()
	return len(names)
