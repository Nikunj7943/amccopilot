frappe.ui.form.on("AMC Payment", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Paid" || !frm.perm[0] || !frm.perm[0].write) return;

		frm.add_custom_button(__("Collect Payment"), () => {
			frappe.call({
				method: "amc_pilot.amcpilot.services.payments.get_payment_options",
				args: { payment: frm.doc.name },
				freeze: true,
				callback(r) {
					const opts = r.message;
					if (opts.method === "razorpay") {
						open_razorpay(frm, opts);
					} else if (opts.method === "upi" && opts.upi_link) {
						window.open(opts.upi_link, "_blank");
					} else {
						frappe.msgprint(__("Set a Business UPI ID in AMC Settings, or configure Razorpay."));
					}
				},
			});
		});

		frm.add_custom_button(__("Mark Paid Manually"), () => {
			frappe.prompt(
				{ fieldtype: "Select", fieldname: "method", label: __("Method"), options: "Cash\nUPI\nCard\nOther", reqd: 1 },
				(values) => {
					frappe.call({
						method: "amc_pilot.amcpilot.services.payments.mark_paid_manually",
						args: { payment: frm.doc.name, method: values.method },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				},
				__("Mark Paid Manually")
			);
		});
	},
});

function open_razorpay(frm, opts) {
	const start = () => {
		const rzp = new Razorpay({
			key: opts.key_id,
			amount: opts.amount,
			currency: "INR",
			name: opts.name,
			order_id: opts.order_id,
			handler(response) {
				frappe.call({
					method: "amc_pilot.amcpilot.services.payments.verify_and_mark_paid",
					args: {
						payment: frm.doc.name,
						razorpay_payment_id: response.razorpay_payment_id,
						razorpay_order_id: response.razorpay_order_id,
						razorpay_signature: response.razorpay_signature,
					},
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			},
		});
		rzp.open();
	};
	if (window.Razorpay) return start();
	frappe.require("https://checkout.razorpay.com/v1/checkout.js", start);
}
