import datetime as dt
import unittest
from unittest.mock import patch

from research.multi_market_observer import (
    MAX_FETCH_ATTEMPTS, SYMBOLS, collect, eligible_cutoff, summarize,
)


class MultiMarketTests(unittest.TestCase):
    def setUp(self):
        start = dt.date(2025, 1, 1)
        self.rows = [
            {"date": (start + dt.timedelta(days=i)).isoformat(), "close": 100 + i}
            for i in range(250)
        ]
        self.now = dt.datetime(2026, 10, 8, 21, tzinfo=dt.timezone.utc)

    def test_session_cutoff_before_close(self):
        now = dt.datetime(2026, 10, 8, 19, 0, tzinfo=dt.timezone.utc)  # 15:00 ET
        self.assertEqual(eligible_cutoff(now), dt.date(2026, 10, 7))

    def test_session_cutoff_after_close(self):
        self.assertEqual(eligible_cutoff(self.now), dt.date(2026, 10, 8))

    def test_filters_future_and_duplicate_bars(self):
        rows = self.rows + [
            {"date": "2026-10-09", "close": 99999},
            {"date": self.rows[-1]["date"], "close": 349},
        ]
        result = summarize("SPY", rows, dt.date(2026, 10, 8))
        self.assertEqual(result["bars"], 250)
        self.assertEqual(result["close"], 349)
        self.assertIsNone(result["signal"])

    def test_six_markets_no_orders(self):
        payload = collect(
            "dummy", self.now,
            fetch=lambda symbol, token, start, end: self.rows,
        )
        self.assertEqual([x["symbol"] for x in payload["results"]], list(SYMBOLS))
        self.assertFalse(payload["orders_enabled"])
        self.assertFalse(payload["strategies_enabled"])
        self.assertTrue(all(x["status"] == "OBSERVATION_ONLY" for x in payload["results"]))
        self.assertTrue(all(x["attempts"] == 1 for x in payload["results"]))

    def test_retries_empty_response_then_recovers(self):
        calls = {"SPY": 0}

        def fetch(symbol, token, start, end):
            if symbol == "SPY":
                calls["SPY"] += 1
                if calls["SPY"] == 1:
                    return []
            return self.rows

        with patch("research.multi_market_observer.time.sleep"):
            payload = collect("dummy", self.now, fetch=fetch)
        spy = payload["results"][0]
        self.assertEqual(calls["SPY"], 2)
        self.assertEqual(spy["status"], "OBSERVATION_ONLY")
        self.assertEqual(spy["attempts"], 2)

    def test_persistent_empty_response_remains_unverified(self):
        with patch("research.multi_market_observer.time.sleep"):
            payload = collect("dummy", self.now, fetch=lambda *args: [])
        spy = payload["results"][0]
        self.assertEqual(spy["status"], "INSUFFICIENT_DATA")
        self.assertEqual(spy["bars"], 0)
        self.assertEqual(spy["attempts"], MAX_FETCH_ATTEMPTS)
        self.assertFalse(payload["orders_enabled"])


if __name__ == "__main__":
    unittest.main()
