from frappe.model.document import Document

from amc_pilot.amcpilot.services.masters import validate_filter_rows, validate_unique_ro_model


class ROModel(Document):
	def validate(self):
		validate_unique_ro_model(self)
		validate_filter_rows(self.model_filters)
