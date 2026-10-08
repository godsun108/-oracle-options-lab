import datetime as dt
import unittest

from research.multi_market_observer import SYMBOLS, collect, eligible_cutoff, summarize


class MultiMarketTests(unittest.TestCase):
    def test_session_cutoff_before_close(self):
        now = dt.datetime(2026, 10, 8, 19, 0, tzinfo=dt.timezone.utc)  # 15:00 ET
        self.assertEqual(eligible_cutoff(now), dt.date(2026, 10, 7))

    def test_session_cutoff_after_close(self):
        now = dt.datetime(2026, 10, 8, 21, 0, tzinfo=dt.timezone.utc)  # 17:00 ET
        self.assertEqual(eligible_cutoff(now), dt.date(2026, 10, 8))

    def test_filters_future_and_duplicate_bars(self):
        rows = [{"date": (dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat(),
                 "close": 100 + i} for i in range(250)]
        rows += [{"date": "2026-10-09", "close": 99999},
                 {"date": rows[-1]["date"], "close": 349}]
        result = summarize("SPY", rows, dt.date(2026, 10, 8))
        self.assertEqual(result["bars"], 250)
        self.assertEqual(result["close"], 349)
        self.assertIsNone(result["signal"])

    def test_six_markets_no_orders(self):
        start = dt.date(2025, 1, 1)
        rows = [{"date": (start + dt.timedelta(days=i)).isoformat(), "close": 100 + i}
                for i in range(250)]
        payload = collect("dummy", dt.datetime(2026, 10, 8, 21, tzinfo=dt.timezone.utc),
                          fetch=lambda symbol, token, s, e: rows)
        self.assertEqual([x["symbol"] for x in payload["results"]], list(SYMBOLS))
        self.assertFalse(payload["orders_enabled"])
        self.assertFalse(payload["strategies_enabled"])
        self.assertTrue(all(x["status"] == "OBSERVATION_ONLY" for x in payload["results"]))


if __name__ == "__main__":
    unittest.main()
