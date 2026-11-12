frappe.ui.form.on("AMC Contract", {
	refresh(frm) {
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
	},
});
