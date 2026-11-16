frappe.query_reports["Parts Due"] = {
	filters: [],
	onload(report) {
		report.page.add_inner_button(__("Create Filter Change Visit"), () => {
			const checked = report.datatable.rowmanager.getCheckedRows().map((i) => report.data[i]);
			if (!checked.length) {
				frappe.msgprint(__("Select one or more rows first."));
				return;
			}
			checked.forEach((row) => {
				frappe.call({
					method: "amc_pilot.amcpilot.services.service_visits.create_filter_change_visit",
					args: { ro_unit: row.ro_unit, service_part: row.service_part },
				});
			});
			frappe.show_alert({ message: __("Visit(s) created."), indicator: "green" });
		});
	},
};
