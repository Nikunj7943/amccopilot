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
def get_plan_defaults(plan: str) -> dict:
	"""What picking `plan` should suggest on the contract form. Nothing is forced:
	the form fills these in and the user can still change every one of them."""
	frappe.has_permission("AMC Plan", "read", throw=True)
	plan_doc = frappe.db.get_value(
		"AMC Plan", plan, ["duration_months", "visits_per_year", "price"], as_dict=True
	)
	if not plan_doc:
		frappe.throw(_("Plan {0} not found.").format(plan))
	visits_included = round((plan_doc.visits_per_year or 0) * (plan_doc.duration_months or 0) / 12)
	return {
		"duration_months": plan_doc.duration_months,
		"amount": plan_doc.price,
		"visits_included": visits_included,
	}


def generate_scheduled_visits(doc) -> int:
	"""Create this Active contract's Scheduled Service Visits, spaced across its
	term (services/scheduling.py). Idempotent: does nothing if the contract
	already has any Service Visit of its own.
	"""
	if frappe.db.exists("Service Visit", {"contract": doc.name}):
		return 0

	from amc_pilot.amcpilot.services.scheduling import generate_visit_dates

	weekly_off = frappe.db.get_single_value("AMC Settings", "weekly_off")
	dates = generate_visit_dates(doc.start_date, doc.end_date, doc.visits_included, weekly_off)
	for visit_date in dates:
		frappe.get_doc(
			{
				"doctype": "Service Visit",
				"ro_unit": doc.ro_unit,
				"contract": doc.name,
				"visit_type": "Scheduled",
				"status": "Scheduled",
				"scheduled_date": visit_date,
			}
		).insert(ignore_permissions=True)
	return len(dates)


def cancel_future_visits(contract_name: str) -> int:
	"""Cancel only this contract's Scheduled visits dated today or later. A
	Completed visit, or one already Cancelled, is left exactly as it is."""
	names = frappe.get_all(
		"Service Visit",
		filters={"contract": contract_name, "status": "Scheduled", "scheduled_date": (">=", today())},
		pluck="name",
	)
	for name in names:
		frappe.db.set_value("Service Visit", name, "status", "Cancelled", update_modified=False)
	return len(names)


@frappe.whitelist()
def activate_contract(contract: str) -> str:
	"""Mark a Draft contract Active and generate its Scheduled visits. Refuses a
	second Active contract on the same unit, and can only run once (a contract
	leaves Draft for good here)."""
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
	generate_scheduled_visits(doc)
	return doc.status


@frappe.whitelist()
def cancel_contract(contract: str) -> str:
	frappe.has_permission("AMC Contract", "write", doc=contract, throw=True)
	doc = frappe.get_doc("AMC Contract", contract)
	if doc.status not in ("Draft", "Active"):
		frappe.throw(_("Only a Draft or Active contract can be cancelled."))
	doc.status = "Cancelled"
	doc.save()
	cancel_future_visits(doc.name)
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


def assign_legacy_default_plan() -> int:
	"""One-time data fix, NOT called automatically by anything.

	Contracts created before AMC Plan existed have plan=None. services/billing.py
	already treats that as Comprehensive coverage (today's Rs.0-while-covered
	behaviour), so nothing breaks by leaving them as they are. This just makes
	that explicit by linking them to a real (inactive, so it never appears in
	the picker for new contracts) "Legacy Comprehensive (Migrated)" plan.

	Run by hand only, after review:
		bench --site amcpilot.localhost execute \
			amc_pilot.amcpilot.services.amc_contracts.assign_legacy_default_plan
	"""
	plan_name = "Legacy Comprehensive (Migrated)"
	if not frappe.db.exists("AMC Plan", plan_name):
		frappe.get_doc(
			{
				"doctype": "AMC Plan",
				"plan_name": plan_name,
				"coverage": "Comprehensive",
				"visits_per_year": 2,
				"is_active": 0,
			}
		).insert(ignore_permissions=True)

	names = frappe.get_all("AMC Contract", filters={"plan": ["in", ["", None]]}, pluck="name")
	for name in names:
		frappe.db.set_value("AMC Contract", name, "plan", plan_name, update_modified=False)
	if names:
		frappe.db.commit()
	return len(names)
