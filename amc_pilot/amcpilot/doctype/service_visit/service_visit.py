from frappe.model.document import Document

from amc_pilot.amcpilot.services.service_visits import on_update, prepare_for_save


class ServiceVisit(Document):
	def validate(self):
		prepare_for_save(self)

	def on_update(self):
		on_update(self)
