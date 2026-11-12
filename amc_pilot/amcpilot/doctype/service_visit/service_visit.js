frappe.ui.form.on("Service Visit", {
	setup(frm) {
		frm.set_query("contract", () => ({ filters: { ro_unit: frm.doc.ro_unit, status: "Active" } }));
	},
});
