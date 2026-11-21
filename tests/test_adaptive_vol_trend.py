import math
import unittest
from datetime import date, timedelta

from research.adaptive_vol_trend import evaluate, target_weight
from research.edge_session_calendar import is_session


def bars(count=280):
    start = date(2025, 1, 1)
    rows = []
    i = 0
    while len(rows) < count:
        day = start + timedelta(days=i)
        i += 1
        if not is_session(day):
            continue
        n = len(rows)
        # Deterministic upward drift with nonzero volatility.
        price = 100.0 * math.exp(0.0012 * n + 0.004 * math.sin(n * 1.71))
        rows.append({"time": day.isoformat(), "open": price})
    return rows


class AdaptiveVolTrendTests(unittest.TestCase):
    def test_insufficient_data_fails_closed(self):
        result = evaluate(bars(202), symbol="SPY")
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertFalse(result["orders_enabled"])
        self.assertEqual(result["observations"], 0)

    def test_exposure_is_capped_and_nonnegative(self):
        weight, reason, features = target_weight([r["open"] for r in bars(220)])
        self.assertGreaterEqual(weight, 0.0)
        self.assertLessEqual(weight, 1.0)
        self.assertIsNotNone(features)
        self.assertIn(reason, ("INVESTED", "TREND_FILTER_OFF", "NO_TRADE_DATA"))

    def test_future_mutation_cannot_change_prior_weights(self):
        source = bars()
        baseline = evaluate(source, symbol="SPY")
        changed = [dict(row) for row in source]
        for i in range(240, len(changed)):
            changed[i]["open"] *= 1.8
        altered = evaluate(changed, symbol="SPY")
        baseline_early = [s["target_weight"] for s in baseline["sessions"]
                          if s["entry_session"] < source[240]["time"]]
        altered_early = [s["target_weight"] for s in altered["sessions"]
                         if s["entry_session"] < source[240]["time"]]
        self.assertEqual(baseline_early, altered_early)

    def test_higher_turnover_cost_cannot_improve_same_path_net_return(self):
        source = bars()
        low = evaluate(source, symbol="SPY", cost_bps_per_full_turnover=0)
        high = evaluate(source, symbol="SPY", cost_bps_per_full_turnover=25)
        self.assertGreaterEqual(low["net_return_pct"], high["net_return_pct"])
        self.assertFalse(high["broker_fills_verified"])
        self.assertFalse(high["edge_proven"])

    def test_invalid_prices_and_chronology_rejected(self):
        source = bars()
        bad_price = [dict(row) for row in source]
        bad_price[210]["open"] = float("nan")
        with self.assertRaises(ValueError):
            evaluate(bad_price, symbol="SPY")
        bad_time = [dict(row) for row in source]
        bad_time[210]["time"] = bad_time[209]["time"]
        with self.assertRaises(ValueError):
            evaluate(bad_time, symbol="SPY")

    def test_unknown_symbol_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(bars(), symbol="XYZ")


if __name__ == "__main__":
    unittest.main()
