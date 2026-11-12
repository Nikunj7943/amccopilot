"""AMC Payment rules: a manual UPI flow that always works, and an optional Razorpay
checkout that turns on automatically once the shop owner fills in both Razorpay keys
in AMC Settings. No code change is needed to switch between them.
"""

import hashlib
import hmac
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import flt, now_datetime
from frappe.utils.password import get_decrypted_password

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"


def _razorpay_keys() -> tuple[str, str] | None:
	key_id = frappe.db.get_single_value("AMC Settings", "razorpay_key_id")
	if not key_id:
		return None
	key_secret = get_decrypted_password("AMC Settings", "AMC Settings", "razorpay_key_secret", raise_exception=False)
	if not key_secret:
		return None
	return key_id, key_secret


def razorpay_configured() -> bool:
	return _razorpay_keys() is not None


def upi_link(amount, note: str) -> str:
	settings = frappe.get_single("AMC Settings")
	if not settings.business_upi_id:
		return ""
	params = (
		f"pa={quote(settings.business_upi_id)}&pn={quote(settings.business_name or 'AMCPilot')}"
		f"&am={flt(amount):.2f}&cu=INR&tn={quote(note)}"
	)
	return f"upi://pay?{params}"


@frappe.whitelist()
def create_payment(contract: str) -> str:
	"""Create a Pending AMC Payment for a contract's amount. Returns the payment name."""
	frappe.has_permission("AMC Contract", "read", doc=contract, throw=True)
	contract_doc = frappe.get_doc("AMC Contract", contract)
	payment = frappe.get_doc(
		{
			"doctype": "AMC Payment",
			"contract": contract_doc.name,
			"amount": contract_doc.amount,
			"status": "Pending",
		}
	)
	payment.insert()
	return payment.name


@frappe.whitelist()
def get_payment_options(payment: str) -> dict:
	"""How to collect this payment: a Razorpay order if keys are set, else a UPI link."""
	frappe.has_permission("AMC Payment", "read", doc=payment, throw=True)
	doc = frappe.get_doc("AMC Payment", payment)
	if doc.status == "Paid":
		return {"method": "paid"}

	keys = _razorpay_keys()
	if keys:
		key_id, key_secret = keys
		if not doc.razorpay_order_id:
			import requests

			response = requests.post(
				RAZORPAY_ORDERS_URL,
				auth=(key_id, key_secret),
				json={"amount": int(flt(doc.amount) * 100), "currency": "INR", "receipt": doc.name},
				timeout=15,
			)
			if response.status_code >= 400:
				frappe.throw(_("Razorpay could not create an order: {0}").format(response.text[:300]))
			order = response.json()
			frappe.db.set_value("AMC Payment", doc.name, "razorpay_order_id", order["id"])
			doc.razorpay_order_id = order["id"]
		return {
			"method": "razorpay",
			"key_id": key_id,
			"order_id": doc.razorpay_order_id,
			"amount": int(flt(doc.amount) * 100),
			"name": frappe.db.get_single_value("AMC Settings", "business_name") or "AMCPilot",
		}

	return {
		"method": "upi",
		"upi_link": upi_link(doc.amount, f"AMC payment {doc.name}"),
	}


@frappe.whitelist()
def verify_and_mark_paid(payment: str, razorpay_payment_id: str, razorpay_order_id: str, razorpay_signature: str) -> str:
	"""Verify Razorpay's signature (HMAC-SHA256 of order_id|payment_id) before marking Paid."""
	frappe.has_permission("AMC Payment", "write", doc=payment, throw=True)
	doc = frappe.get_doc("AMC Payment", payment)
	if doc.razorpay_order_id != razorpay_order_id:
		frappe.throw(_("Order ID does not match this payment."))

	keys = _razorpay_keys()
	if not keys:
		frappe.throw(_("Razorpay is not configured."))
	_key_id, key_secret = keys

	expected = hmac.new(
		key_secret.encode(), f"{razorpay_order_id}|{razorpay_payment_id}".encode(), hashlib.sha256
	).hexdigest()
	if not hmac.compare_digest(expected, razorpay_signature or ""):
		frappe.throw(_("Payment signature could not be verified."))

	_mark_paid(doc, method="Razorpay", razorpay_payment_id=razorpay_payment_id)
	return "Paid"


@frappe.whitelist()
def mark_paid_manually(payment: str, method: str = "Cash") -> str:
	"""Owner confirms a cash/UPI payment by hand. No gateway involved."""
	frappe.has_permission("AMC Payment", "write", doc=payment, throw=True)
	doc = frappe.get_doc("AMC Payment", payment)
	if doc.status == "Paid":
		return "Paid"
	_mark_paid(doc, method=method)
	return "Paid"


def _mark_paid(doc, method: str, razorpay_payment_id: str | None = None) -> None:
	doc.status = "Paid"
	doc.method = method
	doc.paid_on = now_datetime()
	if razorpay_payment_id:
		doc.razorpay_payment_id = razorpay_payment_id
	doc.save(ignore_permissions=True)

	if doc.contract:
		contract = frappe.get_doc("AMC Contract", doc.contract)
		paid_total = frappe.db.sql(
			"select coalesce(sum(amount), 0) from `tabAMC Payment` where contract = %s and status = 'Paid'",
			(doc.contract,),
		)[0][0]
		new_status = "Paid" if flt(paid_total) >= flt(contract.amount) else "Partial"
		frappe.db.set_value("AMC Contract", doc.contract, "payment_status", new_status)
