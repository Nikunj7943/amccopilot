from frappe.model.document import Document

from amc_pilot.amcpilot.services.ro_units import prepare_for_save


class ROUnit(Document):
	def validate(self):
		prepare_for_save(self)
