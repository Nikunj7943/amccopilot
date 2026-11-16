"""Technician isolation on Service Visit: a technician sees and edits only the
visits assigned to them (Service Visit.technician -> AMC Technician.user).

AMC Owner and System Manager are never restricted. A session with no AMC
Technician record (Administrator, Guest, a script, AMC Owner who isn't also a
technician) is left alone here too: doc-level read/write for them is decided
by the DocType's own role permissions, same as before this file existed.
"""

import frappe
from frappe import _


def _is_privileged(user: str) -> bool:
	roles = frappe.get_roles(user)
	return "System Manager" in roles or "AMC Owner" in roles


def _technician_of(user: str) -> str | None:
	return frappe.db.get_value("AMC Technician", {"user": user}, "name")


def service_visit_query_conditions(user: str | None = None) -> str:
	"""Hooked as `permission_query_conditions["Service Visit"]`."""
	user = user or frappe.session.user
	if _is_privileged(user):
		return ""

	technician = _technician_of(user)
	if not technician:
		return ""  # not a technician session; role permissions alone decide access

	return f"`tabService Visit`.technician = {frappe.db.escape(technician)}"


def service_visit_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	"""Hooked as `has_permission["Service Visit"]`.

	Frappe's controller-permission hooks can only ever DENY: returning a falsy
	value here overrides the role permission to "no access", and any other
	value leaves the role-permission decision as it was (see
	`has_controller_permissions` in frappe/permissions.py - `not None` is
	truthy-falsy too, so this must return True, never None, to mean "no
	opinion"). Only a technician session is actually judged here.
	"""
	user = user or frappe.session.user
	if _is_privileged(user):
		return True

	technician = _technician_of(user)
	if not technician:
		return True

	return doc.technician == technician


def enforce_technician_isolation(doc) -> None:
	"""Called from the Service Visit controller's validate(). Defence in depth
	beyond the permission hooks above, and the place that blocks a technician
	from reassigning a visit or editing one that is already Completed.
	"""
	user = frappe.session.user
	if _is_privileged(user):
		return

	technician = _technician_of(user)
	if not technician:
		return  # not a technician session (Guest/QR, Administrator, a service-layer script)

	if doc.technician and doc.technician != technician:
		frappe.throw(_("You can only work on visits assigned to you."), frappe.PermissionError)

	if not doc.is_new() and doc.has_value_changed("technician"):
		frappe.throw(_("You cannot reassign the technician on a visit."), frappe.PermissionError)

	if not doc.is_new():
		before = doc.get_doc_before_save()
		if before and before.status == "Completed":
			frappe.throw(_("A completed visit can no longer be edited."), frappe.PermissionError)
