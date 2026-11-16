"""Renewal and filter-due reminders: who is due, and the WhatsApp text to send them.

No message is sent by this app. It builds a wa.me link that opens WhatsApp (web or app)
with the text pre-filled, and the shop owner or technician sends it with one tap.
"""

from urllib.parse import quote

import frappe
from frappe.utils import add_days, cint, flt, getdate, today

DEFAULT_TEMPLATES = [
	(
		"Renewal Reminder",
		"English",
		"Hello {customer_name}, your AMC with {business_name} for your RO expires on {end_date} "
		"({days_left} days left). Renewal amount: Rs.{amount}. Pay via UPI: {upi_id}. "
		"Reply to book your renewal visit.",
	),
	(
		"Filter Due Reminder",
		"English",
		"Hello {customer_name}, the {part_name} in your RO is due for change around {due_date}. "
		"Please call {business_name} ({owner_mobile}) to schedule a visit.",
	),
	(
		"Visit Reminder",
		"English",
		"Hello {customer_name}, this is a reminder that our technician will visit tomorrow "
		"for your RO service. - {business_name}",
	),
	(
		"Payment Receipt",
		"English",
		"Hello {customer_name}, we have received payment of Rs.{amount} for your AMC with "
		"{business_name}. Thank you!",
	),
]


def ensure_default_templates() -> None:
	"""Insert the default wording for each template type/language once. Never overwrites an edit."""
	for template_type, language, message in DEFAULT_TEMPLATES:
		if not frappe.db.exists("Message Template", {"template_type": template_type, "language": language}):
			frappe.get_doc(
				{
					"doctype": "Message Template",
					"template_type": template_type,
					"language": language,
					"message": message,
				}
			).insert(ignore_permissions=True)
	frappe.db.commit()


def _reminder_days() -> list[int]:
	raw = frappe.db.get_single_value("AMC Settings", "renewal_reminder_days") or "30,15,7,0"
	days = []
	for part in raw.split(","):
		part = part.strip()
		if part.lstrip("-").isdigit():
			days.append(int(part))
	return days or [30, 15, 7, 0]


def get_renewal_reminders() -> list[dict]:
	"""Active contracts whose end_date is exactly one of the configured reminder points away."""
	rows = []
	for days_left in _reminder_days():
		target = add_days(today(), days_left)
		contracts = frappe.get_all(
			"AMC Contract",
			filters={"status": "Active", "end_date": target},
			fields=["name", "customer", "customer_name", "ro_unit", "end_date", "amount"],
		)
		for c in contracts:
			c["days_left"] = days_left
			c["mobile_no"] = frappe.db.get_value("AMC Customer", c.customer, "mobile_no")
			rows.append(c)
	return rows


def get_filters_due_within(days: int) -> list[dict]:
	"""RO Unit filters (on Active units) whose next_due_on is within `days` from today,
	or already overdue. The one query both the Reminders page and the Parts Due
	report are built on - change it here, not in either caller.
	"""
	cutoff = add_days(today(), days)
	return frappe.db.sql(
		"""
		select ruf.parent as ro_unit, ruf.service_part, ruf.next_due_on,
			u.customer, c.customer_name, c.mobile_no
		from `tabRO Unit Filter` ruf
		inner join `tabRO Unit` u on u.name = ruf.parent
		inner join `tabAMC Customer` c on c.name = u.customer
		where ruf.next_due_on is not null and ruf.next_due_on <= %s and u.status = 'Active'
		order by ruf.next_due_on asc
		""",
		(cutoff,),
		as_dict=True,
	)


def get_filter_due_reminders() -> list[dict]:
	"""RO Unit filters whose next_due_on is `visit_reminder_days_before` days away, or overdue."""
	days_before = cint(frappe.db.get_single_value("AMC Settings", "visit_reminder_days_before")) or 1
	return get_filters_due_within(days_before)




def _fill(message: str, **context) -> str:
	safe = {k: ("" if v is None else v) for k, v in context.items()}
	try:
		return message.format(**safe)
	except (KeyError, IndexError):
		return message


def _get_template(template_type: str, language: str | None) -> str:
	name = frappe.db.get_value(
		"Message Template", {"template_type": template_type, "language": language or "English"}, "name"
	) or frappe.db.get_value("Message Template", {"template_type": template_type, "language": "English"}, "name")
	if not name:
		frappe.throw(frappe._("No Message Template is set up for {0}.").format(template_type))
	return frappe.db.get_value("Message Template", name, "message")


def _shop_context() -> dict:
	settings = frappe.get_single("AMC Settings")
	return {
		"business_name": settings.business_name or "",
		"owner_mobile": settings.owner_mobile or "",
		"upi_id": settings.business_upi_id or "",
	}


def whatsapp_link(mobile_no: str, message: str) -> str:
	digits = "".join(ch for ch in (mobile_no or "") if ch.isdigit())
	if len(digits) == 10:
		digits = "91" + digits
	return f"https://wa.me/{digits}?text={quote(message)}"


def build_renewal_message(contract: dict) -> dict:
	language = frappe.db.get_value("AMC Customer", contract["customer"], "preferred_language")
	template = _get_template("Renewal Reminder", language)
	message = _fill(
		template,
		customer_name=contract.get("customer_name"),
		end_date=frappe.utils.formatdate(contract.get("end_date")),
		days_left=contract.get("days_left"),
		amount=int(flt(contract.get("amount"))),
		**_shop_context(),
	)
	return {"message": message, "link": whatsapp_link(contract.get("mobile_no"), message)}


def build_filter_due_message(row: dict) -> dict:
	language = frappe.db.get_value("AMC Customer", row["customer"], "preferred_language")
	template = _get_template("Filter Due Reminder", language)
	message = _fill(
		template,
		customer_name=row.get("customer_name"),
		part_name=row.get("service_part"),
		due_date=frappe.utils.formatdate(row.get("next_due_on")),
		**_shop_context(),
	)
	return {"message": message, "link": whatsapp_link(row.get("mobile_no"), message)}


@frappe.whitelist()
def get_reminders() -> dict:
	"""Single entry point for the Reminders page: everything due today, with ready-to-send text."""
	frappe.has_permission("AMC Contract", "read", throw=True)
	renewals = [dict(c, **build_renewal_message(c)) for c in get_renewal_reminders()]
	filters_due = [dict(r, **build_filter_due_message(r)) for r in get_filter_due_reminders()]
	return {"renewals": renewals, "filters_due": filters_due}
