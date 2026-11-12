from frappe.model.document import Document

from amc_pilot.amcpilot.services.amc_contracts import prepare_for_save


class AMCContract(Document):
	def validate(self):
		prepare_for_save(self)
