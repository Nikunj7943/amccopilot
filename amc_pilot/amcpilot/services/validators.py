"""Shared input validators. Business rules about field values live here only."""

import re

import frappe
from frappe import _

MOBILE_PATTERN = re.compile(r"^[6-9][0-9]{9}$")


def normalize_mobile(value, label: str = "Mobile number", required: bool = False) -> str | None:
	"""Return the 10-digit Indian mobile number, or raise a validation error.

	Strips spaces and dashes, then a leading +91 / 91 / 0 (the prefix is removed only when
	what is left can be a 10-digit number, so 9123456789 stays as it is).
	Empty input returns None unless `required` is set.
	"""
	text = (value or "").strip() if isinstance(value, str) else ("" if value is None else str(value))
	number = re.sub(r"[\s\-]", "", text)

	if not number:
		if required:
			frappe.throw(_("{0} is required.").format(_(label)), title=_("Invalid Mobile Number"))
		return None

	if number.startswith("+91"):
		number = number[3:]
	elif number.startswith("91") and len(number) == 12:
		number = number[2:]
	elif number.startswith("0") and len(number) == 11:
		number = number[1:]

	if not MOBILE_PATTERN.match(number):
		frappe.throw(
			_("{0} must be a 10-digit Indian mobile number starting with 6, 7, 8 or 9. You entered: {1}").format(
				_(label), frappe.bold(text)
			),
			title=_("Invalid Mobile Number"),
		)
	return number


def normalize_mobile_field(doc, fieldname: str, required: bool = False) -> None:
	"""Normalise `doc.<fieldname>` in place, using the field's label in the error message."""
	label = doc.meta.get_label(fieldname) or fieldname
	doc.set(fieldname, normalize_mobile(doc.get(fieldname), label=label, required=required))
