import unittest
from datetime import datetime

from research.edge_session_calendar import (
    eligible_cutoff, session_bounds, next_session, validate_sequence,
)
from research.edge_forward_paper import advance
from tests.test_edge_forward_paper import report


class SessionCalendarTests(unittest.TestCase):
    def test_holiday_and_exception_are_not_sessions(self):
        for day in ("2026-07-03", "2025-01-09", "2026-11-26"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "NON_SESSION"):
                session_bounds(day)
        self.assertEqual(next_session("2026-07-02"), "2026-07-06")

    def test_early_close_plus_publication_buffer(self):
        self.assertEqual(eligible_cutoff(datetime.fromisoformat("2026-11-27T18:14:59+00:00")).isoformat(), "2026-11-25")
        self.assertEqual(eligible_cutoff(datetime.fromisoformat("2026-11-27T18:15:00+00:00")).isoformat(), "2026-11-27")

    def test_dst_and_bank_holiday_equity_session(self):
        self.assertEqual(session_bounds("2026-03-06")[0].hour, 14)
        self.assertEqual(session_bounds("2026-03-09")[0].hour, 13)
        self.assertEqual(session_bounds("2026-11-02")[0].hour, 14)
        self.assertEqual(session_bounds("2026-10-12")[1].hour, 20)

    def test_unknown_coverage_and_naive_time_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "COVERAGE_UNAVAILABLE"):
            session_bounds("2028-01-03")
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            eligible_cutoff(datetime(2026, 10, 12))

    def test_missing_session_cannot_extend_holding_period(self):
        with self.assertRaisesRegex(ValueError, "MISSING_MARKET_SESSION"):
            validate_sequence(["2026-10-05", "2026-10-07"])
        first = advance(None, report("2026-10-05", [("2026-10-05", 100.0)]))
        with self.assertRaisesRegex(ValueError, "MISSING_MARKET_SESSION"):
            advance(first, report("2026-10-07", [("2026-10-05", 100.0), ("2026-10-07", 105.0)]))

    def test_future_or_stale_source_does_not_register(self):
        for observed in ("2026-10-05T13:29:00+00:00", "2026-10-06T21:00:00+00:00"):
            source = report("2026-10-05", [("2026-10-05", 100.0)])
            source["observed_at"] = observed
            with self.subTest(observed=observed), self.assertRaisesRegex(ValueError, "STALE_OR_FUTURE"):
                advance(None, source)

    def test_registration_clock_is_distinct_from_source_clock(self):
        source = report("2026-10-05", [("2026-10-05", 100.0)])
        first = advance(None, source, registered_at="2026-10-06T14:00:00+00:00")
        signal = next(e for e in first["events"] if e["type"] == "SIGNAL_REGISTERED")
        self.assertEqual(signal["registered_at"], "2026-10-06T14:00:00+00:00")
        self.assertEqual(signal["source_observed_at"], source["observed_at"])
        with self.assertRaisesRegex(ValueError, "registration precedes"):
            advance(None, source, registered_at="2026-10-05T20:00:00+00:00")

    def test_holiday_outcome_uses_next_real_session(self):
        first = advance(None, report("2026-07-02", [("2026-07-02", 100.0)]))
        later = advance(first, report("2026-07-07", [("2026-07-02", 100.0),
                        ("2026-07-06", 101.0), ("2026-07-07", 102.0)]))
        outcomes = [e for e in later["events"] if e["type"] == "PAPER_OUTCOME_OBSERVED"]
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes[0]["entry_date"], "2026-07-06")


if __name__ == "__main__":
    unittest.main()
