frappe.ui.form.on("RO Unit", {
	setup(frm) {
		frm.set_query("service_part", "unit_filters", () => ({ filters: { is_filter: 1 } }));
	},

	refresh(frm) {
		if (frm.is_new() || !frm.perm[0] || !frm.perm[0].write) return;

		frm.add_custom_button(__("Reload filters from model"), () => {
			if (frm.is_dirty()) {
				frappe.msgprint(__("Please save the unit first."));
				return;
			}
			frappe.call({
				method: "amc_pilot.amcpilot.services.ro_units.reload_filters_from_model",
				args: { ro_unit: frm.doc.name },
				freeze: true,
				callback(r) {
					const added = r.message || 0;
					frappe.show_alert({
						message: added
							? __("{0} filter(s) added from the model.", [added])
							: __("No missing filters. Nothing changed."),
						indicator: added ? "green" : "blue",
					});
					frm.reload_doc();
				},
			});
		});
	},
});
