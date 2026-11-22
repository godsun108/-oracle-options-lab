import math
import unittest
from datetime import date, timedelta

from research.adaptive_vol_comparison import compare_market
from research.edge_session_calendar import is_session


def bars(count=280):
    start = date(2025, 1, 1)
    rows = []
    offset = 0
    while len(rows) < count:
        day = start + timedelta(days=offset)
        offset += 1
        if not is_session(day):
            continue
        n = len(rows)
        price = 100.0 * math.exp(0.0012 * n + 0.004 * math.sin(n * 1.71))
        rows.append({"time": day.isoformat(), "open": price})
    return rows


class AdaptiveVolComparisonTests(unittest.TestCase):
    def test_all_controls_share_identical_paired_window(self):
        result = compare_market(bars(), symbol="SPY")
        self.assertEqual(result["status"], "HISTORICAL_PAIRED_EXPLORATORY_ONLY")
        self.assertTrue(result["paired_dates_identical"])
        self.assertEqual(
            set(result["strategies"]),
            {"adaptive_vol_trend_001", "tsmom_63", "trend_200", "buy_hold", "zero_yield_cash"},
        )
        counts = {row["observations"] for row in result["strategies"].values()}
        self.assertEqual(counts, {result["paired_sessions"]})

    def test_metrics_and_safety_flags_are_present(self):
        result = compare_market(bars(), symbol="SPY")
        candidate = result["strategies"]["adaptive_vol_trend_001"]
        for field in (
            "net_return_pct", "gross_return_pct", "max_drawdown_pct",
            "annualized_net_volatility_pct", "worst_session_net_return_pct",
            "total_assumed_cost", "total_turnover_full_weight_units",
            "rebalance_count_including_final_liquidation", "average_exposure",
            "time_in_cash_fraction", "excess_vs_better_trend_control_pct",
            "excess_vs_buy_hold_pct",
        ):
            self.assertIn(field, candidate)
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["broker_fills_verified"])
        self.assertFalse(result["edge_proven"])
        self.assertFalse(result["eligible_for_live_trading"])

    def test_higher_costs_do_not_improve_any_strategy_net_return(self):
        source = bars()
        low = compare_market(source, symbol="SPY", cost_bps_per_full_turnover=0)
        high = compare_market(source, symbol="SPY", cost_bps_per_full_turnover=25)
        for strategy_id in low["strategies"]:
            self.assertGreaterEqual(
                low["strategies"][strategy_id]["net_return_pct"],
                high["strategies"][strategy_id]["net_return_pct"],
            )

    def test_unknown_market_rejected(self):
        with self.assertRaises(ValueError):
            compare_market(bars(), symbol="XYZ")

    def test_insufficient_data_fails_closed(self):
        result = compare_market(bars(202), symbol="SPY")
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["paired_sessions"], 0)
        self.assertFalse(result["orders_enabled"])


if __name__ == "__main__":
    unittest.main()
