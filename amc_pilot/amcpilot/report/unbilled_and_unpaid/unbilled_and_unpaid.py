"""Completed visits where the customer owes more than they have paid on the spot.

Does not include contract-level AMC Payment (renewal) amounts - this is only
what was chargeable at the visit itself (services/billing.py).
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	return get_columns(), get_data()


def get_columns():
	return [
		{"label": _("Visit"), "fieldname": "name", "fieldtype": "Link", "options": "Service Visit", "width": 120},
		{"label": _("RO Unit"), "fieldname": "ro_unit", "fieldtype": "Link", "options": "RO Unit", "width": 120},
		{"label": _("Customer"), "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Scheduled Date"), "fieldname": "scheduled_date", "fieldtype": "Date", "width": 110},
		{"label": _("Total Chargeable"), "fieldname": "total_chargeable", "fieldtype": "Currency", "options": "INR", "width": 130},
		{"label": _("Payment Collected"), "fieldname": "payment_collected", "fieldtype": "Currency", "options": "INR", "width": 140},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "options": "INR", "width": 120},
	]


def get_data():
	rows = frappe.db.sql(
		"""
		select v.name, v.ro_unit, c.customer_name, v.scheduled_date, v.total_chargeable, v.payment_collected
		from `tabService Visit` v
		inner join `tabAMC Customer` c on c.name = v.customer
		where v.status = 'Completed'
			and coalesce(v.total_chargeable, 0) > coalesce(v.payment_collected, 0)
		order by v.scheduled_date desc
		""",
		as_dict=True,
	)
	for row in rows:
		row.outstanding = flt(row.total_chargeable) - flt(row.payment_collected)
	return rows
