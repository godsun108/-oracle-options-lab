import copy
import unittest
from research.agent_trade_cycles import build
from research.edge_forward_paper import advance
from tests.test_edge_forward_paper import report
from tests.test_edge_forward_integrity_audit import rehash


def cycle(exit_price=110, sell=True):
    ledger = None
    opens = []
    for day, price, target in [('2026-10-05', 100, 1), ('2026-10-06', 100, 0 if sell else 1), ('2026-10-07', exit_price, 0 if sell else 1)]:
        opens.append((day, price))
        r = report(day, opens[:])
        r['reports'][0]['strategies'][0]['next_session_paper_signal'] = target
        ledger = advance(ledger, r)
    return ledger


class TradeCycleTests(unittest.TestCase):
    def test_buy_sell_with_costs_and_source_links(self):
        d = build(cycle())
        self.assertEqual(d['closed_trade_count'], 1)
        a = next(x for x in d['agents'] if x['agent_id'] == 'SPY::tsmom_63')
        t = a['closed_trades'][0]
        self.assertAlmostEqual(t['net_pnl'], (2000 / 100.1) * 110 * .999 - 2000)
        self.assertAlmostEqual(a['equity'] - 2000, t['net_pnl'])
        for side in ('entry', 'exit'):
            self.assertEqual(len(t[side]['signal_sha256']), 64)
            self.assertEqual(len(t[side]['source_checkpoint_sha256']), 64)
        self.assertFalse(d['broker_fills_verified'])
        self.assertFalse(d['orders_enabled'])

    def test_losing_and_flat_price_trades_include_costs(self):
        for price in (90, 100):
            with self.subTest(price=price):
                a = next(x for x in build(cycle(price))['agents'] if x['agent_id'] == 'SPY::tsmom_63')
                self.assertLess(a['realized_pnl'], 0)
                self.assertEqual(a['unrealized_pnl'], 0)

    def test_open_hold_is_not_closed_profit(self):
        d = build(cycle(sell=False))
        self.assertEqual(d['closed_trade_count'], 0)
        self.assertEqual(d['open_trade_count'], 1)
        a = next(x for x in d['agents'] if x['agent_id'] == 'SPY::tsmom_63')
        self.assertEqual(a['realized_pnl'], 0)
        self.assertGreater(a['unrealized_pnl'], 0)

    def test_repeated_report_is_deterministic(self):
        ledger = cycle()
        before = copy.deepcopy(ledger)
        self.assertEqual(build(ledger), build(ledger))
        self.assertEqual(ledger, before)

    def test_forged_profit_and_late_signal_fail_semantic_audit(self):
        for kind in ('profit', 'late'):
            ledger = cycle()
            for e in ledger['events']:
                if kind == 'profit' and e['type'] == 'PAPER_OUTCOME_OBSERVED':
                    e['hypothetical_net_return_pct'] = 1000
                    break
                if kind == 'late' and e['type'] == 'SIGNAL_REGISTERED':
                    e['registered_at'] = '2026-10-07T22:00:00+00:00'
                    break
            rehash(ledger)
            with self.assertRaises(ValueError):
                build(ledger)


if __name__ == '__main__':
    unittest.main()
