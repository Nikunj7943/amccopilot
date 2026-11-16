"""RO Unit filters due within N days (default 15). Same query the Reminders
page uses (amcpilot.services.reminders.get_filters_due_within) - not copied.
"""

from frappe import _
from frappe.utils import cint

from amc_pilot.amcpilot.services.reminders import get_filters_due_within


def execute(filters=None):
	filters = filters or {}
	days = cint(filters.get("days")) or 15
	return get_columns(), get_filters_due_within(days)


def get_columns():
	return [
		{"label": _("RO Unit"), "fieldname": "ro_unit", "fieldtype": "Link", "options": "RO Unit", "width": 120},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Mobile"), "fieldname": "mobile_no", "fieldtype": "Data", "width": 110},
		{"label": _("Service Part"), "fieldname": "service_part", "fieldtype": "Link", "options": "Service Part", "width": 150},
		{"label": _("Next Due On"), "fieldname": "next_due_on", "fieldtype": "Date", "width": 110},
	]
