from frappe.model.document import Document

from amc_pilot.amcpilot.services.validators import normalize_mobile_field


class AMCCustomer(Document):
	def validate(self):
		normalize_mobile_field(self, "mobile_no", required=True)
		normalize_mobile_field(self, "alt_mobile")
