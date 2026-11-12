from frappe.model.document import Document

from amc_pilot.amcpilot.services.masters import is_filter_type


class ServicePart(Document):
	def validate(self):
		self.part_name = (self.part_name or "").strip()
		self.is_filter = is_filter_type(self.part_type)
