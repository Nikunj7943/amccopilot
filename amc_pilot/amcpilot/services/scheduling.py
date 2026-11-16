"""Pure date math for spacing an AMC contract's visits across its term.

No database access here on purpose: it is easy to test and easy to trust.
"""

from frappe.utils import add_days, getdate

_WEEKDAY_INDEX = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}


def _push_past_weekly_off(date, weekly_off: str | None):
	off_index = _WEEKDAY_INDEX.get(weekly_off)
	if off_index is None:
		return date
	while date.weekday() == off_index:
		date = add_days(date, 1)
	return date


def generate_visit_dates(start_date, end_date, n_visits, weekly_off: str | None = None) -> list:
	"""n_visits dates, evenly spaced across (start_date, end_date].

	- interval = (end_date - start_date) / n_visits; visit i lands at
	  start_date + round(interval * i).
	- No date lands later than end_date - 7 days.
	- A date that falls on the shop's weekly-off day moves to the next day
	  (applied after the above clamp, so it can push a day or two past the
	  clamp rather than skip a visit).
	- Returns [] for a non-positive visit count or a term that is not
	  positive in length.
	"""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	n_visits = int(n_visits or 0)
	if n_visits <= 0:
		return []

	total_days = (end_date - start_date).days
	if total_days <= 0:
		return []

	interval_days = total_days / n_visits
	last_allowed = add_days(end_date, -7)
	if last_allowed < start_date:
		last_allowed = end_date

	dates = []
	for i in range(1, n_visits + 1):
		visit_date = add_days(start_date, round(interval_days * i))
		if visit_date > last_allowed:
			visit_date = last_allowed
		visit_date = _push_past_weekly_off(visit_date, weekly_off)
		dates.append(visit_date)
	return dates
