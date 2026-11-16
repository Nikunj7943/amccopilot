frappe.ui.form.on("AMC Contract", {
	plan(frm) {
		if (!frm.doc.plan || !frm.doc.__islocal) return;
		// Only auto-fill on a still-new contract, and only suggest: every field stays editable after.
		frappe.call({
			method: "amc_pilot.amcpilot.services.amc_contracts.get_plan_defaults",
			args: { plan: frm.doc.plan },
			callback(r) {
				if (!r.message) return;
				frm.set_value("duration_months", r.message.duration_months);
				frm.set_value("amount", r.message.amount);
				frm.set_value("visits_included", r.message.visits_included);
			},
		});
	},

	refresh(frm) {
		frm.set_query("plan", () => ({ filters: { is_active: 1 } }));
		if (frm.is_new() || !frm.perm[0] || !frm.perm[0].write) return;

		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__("Activate"), () => {
				frappe.call({
					method: "amc_pilot.amcpilot.services.amc_contracts.activate_contract",
					args: { contract: frm.doc.name },
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			});
		}
		if (["Draft", "Active"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel Contract"), () => {
				frappe.confirm(__("Cancel this contract?"), () => {
					frappe.call({
						method: "amc_pilot.amcpilot.services.amc_contracts.cancel_contract",
						args: { contract: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				});
			});
		}
		if (frm.doc.payment_status !== "Paid") {
			frm.add_custom_button(__("Collect Payment"), () => {
				frappe.call({
					method: "amc_pilot.amcpilot.services.payments.create_payment",
					args: { contract: frm.doc.name },
					freeze: true,
					callback(r) {
						frappe.set_route("Form", "AMC Payment", r.message);
					},
				});
			});
		}
	},
});
