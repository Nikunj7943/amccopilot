frappe.pages["amcpilot-reminders"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Reminders"),
		single_column: true,
	});

	page.add_inner_button(__("Refresh"), () => load());

	const $body = $('<div class="amc-reminders"></div>').appendTo(page.body);

	function row(item, kind) {
		const heading =
			kind === "renewal"
				? __("{0} — AMC ends {1} ({2} days left)", [item.customer_name, item.end_date, item.days_left])
				: __("{0} — {1} due {2}", [item.customer_name, item.service_part, item.next_due_on]);

		return $(`
			<div class="amc-reminder-row" style="display:flex;justify-content:space-between;align-items:center;
				padding:10px 12px;border-bottom:1px solid var(--border-color);">
				<div>
					<div style="font-weight:600;">${frappe.utils.escape_html(heading)}</div>
					<div class="text-muted" style="font-size:12px;">${frappe.utils.escape_html(item.message)}</div>
				</div>
				<a class="btn btn-sm btn-primary" target="_blank" href="${item.link}">${__("Send on WhatsApp")}</a>
			</div>
		`);
	}

	function section(title, items, kind) {
		const $s = $(`<div style="margin-bottom:24px;"><h5>${frappe.utils.escape_html(title)} (${items.length})</h5></div>`);
		if (!items.length) {
			$s.append(`<div class="text-muted">${__("Nothing due.")}</div>`);
		}
		items.forEach((item) => $s.append(row(item, kind)));
		return $s;
	}

	function load() {
		$body.html(`<div class="text-muted">${__("Loading...")}</div>`);
		frappe.call({
			method: "amc_pilot.amcpilot.services.reminders.get_reminders",
			callback(r) {
				const data = r.message || { renewals: [], filters_due: [] };
				$body.empty();
				$body.append(section(__("AMC Renewals Due"), data.renewals, "renewal"));
				$body.append(section(__("Filters Due for Change"), data.filters_due, "filter"));
			},
		});
	}

	load();
};
