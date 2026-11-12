"""Numbers for the AMCPilot workspace's stat cards. Business logic only; the
Number Card / Dashboard Chart records just call into this.
"""

import frappe
from frappe.utils import getdate, today


@frappe.whitelist()
def overdue_filters_count(filters=None) -> int:
	"""Filters on an Active RO Unit whose Next Due On date has already passed."""
	frappe.has_permission("RO Unit", "read", throw=True)
	return frappe.db.sql(
		"""
		select count(*) from `tabRO Unit Filter` ruf
		inner join `tabRO Unit` u on u.name = ruf.parent
		where ruf.next_due_on is not null and ruf.next_due_on < %s and u.status = 'Active'
		""",
		(today(),),
	)[0][0]
