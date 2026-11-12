import frappe

from amc_pilot.amcpilot.services.guest_portal import build_portal_context, get_unit_by_token

no_cache = 1


def get_context(context):
	token = frappe.form_dict.get("token")
	unit = get_unit_by_token(token)
	if not unit:
		frappe.local.flags.redirect_location = "/"
		raise frappe.Redirect

	context.update(build_portal_context(unit))
	context.token = token
	context.no_sidebar = True
