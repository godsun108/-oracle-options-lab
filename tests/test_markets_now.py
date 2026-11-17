import unittest
from datetime import datetime, timezone

from research.markets_now import (
    empty_snapshot, market_session, score_contract, collect, _trend,
)


NOW = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)


def option(**overrides):
    row = {
        "symbol": "SPY261231C00600000",
        "option_type": "call",
        "strike": 600,
        "bid": 1.00,
        "ask": 1.02,
        "open_interest": 1200,
        "volume": 150,
        "bid_size": 20,
        "ask_size": 18,
        "greeks": {"delta": 0.45, "mid_iv": 0.22},
    }
    row.update(overrides)
    return row


class MarketsNowTests(unittest.TestCase):
    def test_missing_secret_returns_explicit_unavailable_snapshot(self):
        result = collect(token="", now=NOW)
        self.assertEqual(result["feed_status"], "UNAVAILABLE")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["edge_proven"])
        self.assertEqual(result["candidates"], [])

    def test_high_quality_contract_is_screened_not_recommended(self):
        result = score_contract(option(), "BULLISH", NOW, "2026-12-31")
        self.assertIsNotNone(result)
        self.assertEqual(result["directional_fit"], "ALIGNED")
        self.assertGreaterEqual(result["screen_score"], 65)
        self.assertFalse(result["orders_enabled"])
        self.assertTrue(result["manual_quote_verification_required"])
        self.assertEqual(result["score_label"], "SCREENING HEURISTIC — NOT WIN PROBABILITY")

    def test_wide_spread_is_rejected(self):
        self.assertIsNone(score_contract(option(ask=1.30), "BULLISH", NOW, "2026-12-31"))

    def test_expired_or_short_dated_contract_is_rejected(self):
        self.assertIsNone(score_contract(option(), "BULLISH", NOW, "2026-11-20"))

    def test_missing_liquidity_is_rejected(self):
        self.assertIsNone(score_contract(option(open_interest=0, volume=0, bid_size=0, ask_size=0),
                                         "BULLISH", NOW, "2026-12-31"))

    def test_old_provider_quote_timestamp_is_rejected(self):
        old = int(datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc).timestamp())
        self.assertIsNone(score_contract(option(bid_date=old, ask_date=old),
                                         "BULLISH", NOW, "2026-12-31"))

    def test_missing_provider_quote_timestamp_is_explicit(self):
        result = score_contract(option(), "BULLISH", NOW, "2026-12-31")
        self.assertFalse(result["quote_timestamp_verified"])
        self.assertIsNone(result["quote_timestamp"])

    def test_trend_requires_enough_history(self):
        self.assertEqual(_trend([100.0] * 20)["trend"], "UNKNOWN")

    def test_market_session_uses_eastern_time(self):
        self.assertEqual(market_session(datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)), "OPEN")
        self.assertEqual(market_session(datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc)), "CLOSED")

    def test_empty_snapshot_never_claims_edge_or_orders(self):
        result = empty_snapshot(NOW, "test")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["edge_proven"])
        self.assertTrue(result["research_only"])


if __name__ == "__main__":
    unittest.main()
