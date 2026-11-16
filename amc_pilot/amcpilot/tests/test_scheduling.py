import unittest

from amc_pilot.amcpilot.services.scheduling import generate_visit_dates


class TestGenerateVisitDates(unittest.TestCase):
	"""Pure function, no DB: plain unittest, not IntegrationTestCase."""

	def test_12_months_4_visits(self):
		dates = generate_visit_dates("2026-01-01", "2027-01-01", 4)
		self.assertEqual(len(dates), 4)
		self.assertEqual(dates, sorted(dates))
		for d in dates:
			self.assertLessEqual(d.isoformat(), "2026-12-25")  # end_date - 7 days

	def test_12_months_3_visits(self):
		dates = generate_visit_dates("2026-01-01", "2027-01-01", 3)
		self.assertEqual(len(dates), 3)
		self.assertEqual(dates, sorted(dates))

	def test_6_months_2_visits(self):
		dates = generate_visit_dates("2026-01-01", "2026-07-01", 2)
		self.assertEqual(len(dates), 2)
		self.assertLessEqual(dates[-1].isoformat(), "2026-06-24")

	def test_leap_year_29_feb_start(self):
		dates = generate_visit_dates("2028-02-29", "2029-02-28", 4)
		self.assertEqual(len(dates), 4)
		self.assertEqual(dates, sorted(dates))
		for d in dates:
			self.assertGreater(d.isoformat(), "2028-02-29")

	def test_weekly_off_shifts_forward(self):
		dates = generate_visit_dates("2026-11-01", "2026-11-29", 4, "Sunday")
		for d in dates:
			self.assertNotEqual(d.weekday(), 6)  # 6 = Sunday

	def test_no_weekly_off_means_no_shift_needed(self):
		dates = generate_visit_dates("2026-01-01", "2027-01-01", 4, None)
		self.assertEqual(len(dates), 4)

	def test_last_visit_never_later_than_end_minus_7(self):
		dates = generate_visit_dates("2026-01-01", "2026-01-20", 1)
		self.assertLessEqual(dates[0].isoformat(), "2026-01-13")

	def test_zero_visits_or_empty_term(self):
		self.assertEqual(generate_visit_dates("2026-01-01", "2027-01-01", 0), [])
		self.assertEqual(generate_visit_dates("2026-01-01", "2026-01-01", 3), [])
		self.assertEqual(generate_visit_dates("2027-01-01", "2026-01-01", 3), [])
