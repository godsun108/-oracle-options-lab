import copy
import unittest
from unittest.mock import patch

from research.edge_forward_paper import advance
from research.edge_paper_league import load_rules, season_windows, standings
from research.edge_session_calendar import next_session
from tests.test_edge_forward_paper import report
from tests.test_edge_forward_integrity_audit import rehash


def synthetic_season():
    """Flat synthetic prices: invested sleeves lose costs, cash earns zero."""
    rules=load_rules()
    day=rules['first_signal_session']
    opens=[]
    ledger=None
    for _ in range(rules['sessions']+2):
        opens.append((day,100.0))
        source=report(day,opens)
        source['observed_at']=day+'T22:00:00Z'
        template=source['reports'][0]
        source['reports']=[]
        for symbol in rules['teams']:
            market=copy.deepcopy(template)
            market['symbol']=symbol
            market['strategies']=[{'strategy_id':sid,'next_session_paper_signal':int(symbol!='QQQ')}
                                  for sid in rules['strategies']]
            source['reports'].append(market)
        ledger=advance(ledger,source)
        day=next_session(day)
    return ledger,opens[-1][0]+'T22:00:00Z'


class LeagueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger,cls.as_of=synthetic_season()

    def test_full_window_equal_capital_costs_and_no_profit_certificate(self):
        before=copy.deepcopy(self.ledger)
        result=standings(self.ledger,as_of=self.as_of)
        self.assertEqual(len(result['descriptive_order_by_net_return']),6)
        self.assertEqual(result['descriptive_order_by_net_return'][0],'QQQ')
        spy=next(r for r in result['teams'] if r['team']=='SPY')
        self.assertEqual(spy['completed_common_sessions'],60)
        self.assertAlmostEqual(spy['net_return_pct'],100*((1-.005)**60-1),places=5)
        self.assertEqual(spy['max_drawdown_pct'],spy['net_return_pct'])
        self.assertEqual(spy['cost_free_market_return_pct'],0)
        self.assertIsNone(result['profitable_team_certified'])
        self.assertFalse(result['eligible_for_live_trading'])
        self.assertEqual(result['hypothesis_family_size'],18)
        self.assertEqual(self.ledger,before)

    def test_old_evidence_does_not_enter_new_season(self):
        ledger=advance(None,report('2026-10-12',[('2026-10-12',100.0)]))
        result=standings(ledger,as_of='2026-10-15T12:00:00Z')
        self.assertEqual(result['descriptive_order_by_net_return'],[])
        self.assertTrue(all(t['completed_common_sessions']==0 and t['net_return_pct'] is None for t in result['teams']))

    def test_missing_team_is_not_cash_and_does_not_hold_other_teams(self):
        ledger=copy.deepcopy(self.ledger)
        ledger['events']=[e for e in ledger['events'] if not(e['symbol']=='IWM' and e['type']=='PAPER_OUTCOME_OBSERVED')]
        removed=180
        ledger['outcomes_observed']-=removed
        ledger['pending_signals']+=removed
        ledger['events_recorded']=len(ledger['events'])
        rehash(ledger)
        result=standings(ledger,as_of=self.as_of)
        iwm=next(t for t in result['teams'] if t['team']=='IWM')
        self.assertEqual(iwm['status'],'INCOMPLETE_EVIDENCE')
        self.assertEqual(len(iwm['missing_eligible_windows']),60)
        self.assertIsNone(iwm['net_return_pct'])
        self.assertEqual(len(result['descriptive_order_by_net_return']),5)

    def test_early_snapshot_cannot_display_future_results(self):
        with self.assertRaisesRegex(ValueError,'not yet eligible'):
            standings(self.ledger,as_of='2026-10-16T22:00:00Z')

    def test_59_sessions_cannot_enter_60_session_ordering(self):
        ledger=copy.deepcopy(self.ledger)
        last_exit=season_windows(load_rules())[-1][1]
        ledger['events']=[e for e in ledger['events'] if not(
            e['symbol']=='SPY' and e['type']=='PAPER_OUTCOME_OBSERVED' and e['exit_date']==last_exit)]
        ledger['outcomes_observed']-=3
        ledger['pending_signals']+=3
        ledger['events_recorded']=len(ledger['events'])
        rehash(ledger)
        result=standings(ledger,as_of=self.as_of)
        spy=next(t for t in result['teams'] if t['team']=='SPY')
        self.assertEqual(spy['completed_common_sessions'],59)
        self.assertIsNone(spy['net_return_pct'])
        self.assertNotIn('SPY',result['descriptive_order_by_net_return'])

    def test_rehashed_fake_profit_rejected(self):
        ledger=copy.deepcopy(self.ledger)
        next(e for e in ledger['events'] if e['type']=='PAPER_OUTCOME_OBSERVED')['hypothetical_net_return_pct']=100
        rehash(ledger)
        with self.assertRaisesRegex(ValueError,'arithmetic mismatch'):
            standings(ledger,as_of=self.as_of)

    def test_changed_implementation_or_late_registration_rejected(self):
        rules=load_rules()
        rules['source_sha256']['research/edge_lab.py']='0'*64
        import json
        with patch('pathlib.Path.read_text',return_value=json.dumps(rules)):
            with self.assertRaisesRegex(ValueError,'implementation changed'):load_rules()
        rules['registered_at']='2026-10-16T22:00:00Z'
        with patch('pathlib.Path.read_text',return_value=json.dumps(rules)):
            with self.assertRaisesRegex(ValueError,'not registered before season'):load_rules()

    def test_season_has_exact_contiguous_windows(self):
        windows=season_windows(load_rules())
        self.assertEqual(len(windows),60)
        self.assertEqual(windows[0],('2026-10-16','2026-10-19'))
        self.assertTrue(all(a[1]==b[0] for a,b in zip(windows,windows[1:])))


if __name__=='__main__':
    unittest.main()
