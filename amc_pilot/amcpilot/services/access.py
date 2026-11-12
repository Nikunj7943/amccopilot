"""Who may see the AMCPilot app on the desk."""

import frappe

APP_ROLES = {"AMC Owner", "AMC Technician", "System Manager"}


def has_app_permission() -> bool:
	"""Used by the `add_to_apps_screen` hook: show the app icon only to AMC users."""
	if frappe.session.user in (None, "Guest"):
		return False
	return bool(APP_ROLES & set(frappe.get_roles(frappe.session.user)))
