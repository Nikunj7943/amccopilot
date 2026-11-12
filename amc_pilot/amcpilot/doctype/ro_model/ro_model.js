frappe.ui.form.on("RO Model", {
	setup(frm) {
		// Only Service Parts of type Filter can be picked (server re-checks in validate).
		frm.set_query("service_part", "model_filters", () => ({ filters: { is_filter: 1 } }));
	},
});
