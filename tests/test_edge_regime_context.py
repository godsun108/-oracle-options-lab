import copy
import unittest
from research.edge_regime_context import describe, validate, labels
from research.edge_forward_paper import advance
from research.edge_forward_integrity_audit import audit
from research.edge_source_replay import audit as replay
from tests import test_edge_source_replay as fixtures
from tests.test_edge_lab import bars


class RegimeTests(unittest.TestCase):
    def test_fixed_labels_and_all_four_quadrants(self):
        for momentum,volatility,label in [(0,0,'UP_OR_FLAT/LOW_VOL'),(-1,19,'DOWN/LOW_VOL'),(1,20,'UP_OR_FLAT/HIGH_VOL'),(-1,21,'DOWN/HIGH_VOL')]:
            self.assertEqual(labels(momentum,volatility),label)
        raw=bars(64)
        clean=[{'time':r['date'],'open':100.0} for r in raw]
        result=describe(clean)
        self.assertEqual(result['momentum_63_pct'],0)
        self.assertEqual(result['annualized_volatility_20_pct'],0)
        self.assertEqual(result['label'],'UP_OR_FLAT/LOW_VOL')
        for sign in (-1,1):
            for i,row in enumerate(clean):row['open']=100*(1.001**(sign*i))
            result=describe(clean)
            self.assertEqual(result['label'],'DOWN/LOW_VOL' if sign<0 else 'UP_OR_FLAT/LOW_VOL')

    def test_bad_prices_or_missing_sessions_fail(self):
        clean=[{'time':r['date'],'open':r['open']} for r in bars(65)]
        for price in (float('nan'),0,True):
            bad=copy.deepcopy(clean);bad[-1]['open']=price
            with self.assertRaises(ValueError):describe(bad)
        with self.assertRaises(ValueError):describe(clean[:20])
        bad=copy.deepcopy(clean);del bad[-3]
        with self.assertRaises(ValueError):describe(bad)

    def test_new_labels_replay_and_old_signals_are_never_backfilled(self):
        from tests.test_edge_lab import REGISTRY
        factory=fixtures.PartialMarketTests()
        current=factory.report()
        replay(current,REGISTRY)
        original=copy.deepcopy(current)
        for m in original['reports']:m.pop('regime_context')
        prior=advance(None,original)
        after=advance(prior,current)
        self.assertEqual(after['events'],prior['events'])
        later=factory.report(13)
        after=advance(after,later)
        added=[e for e in after['events'][len(prior['events']):] if e['type']=='SIGNAL_REGISTERED']
        self.assertEqual(len(added),18)
        self.assertTrue(all(e['regime_context']['as_of_session']=='2026-10-13' for e in added))
        audit(after)
        later['reports'][0]['regime_context']['label']='BROKEN'
        self.assertNotEqual(added[0]['regime_context']['label'],'BROKEN')
        with self.assertRaises(ValueError):replay(later,REGISTRY)

    def test_future_or_mutated_context_rejected(self):
        from tests.test_edge_forward_integrity_audit import rehash
        current=fixtures.PartialMarketTests().report()
        for change in ('future','threshold','label'):
            bad=copy.deepcopy(current)
            context=bad['reports'][0]['regime_context']
            context[{'future':'as_of_session','threshold':'volatility_threshold_pct','label':'label'}[change]]={'future':'2026-10-13','threshold':21,'label':'WRONG'}[change]
            with self.assertRaises(ValueError):advance(None,bad)
        ledger=advance(None,current)
        next(e for e in ledger['events'] if e['type']=='SIGNAL_REGISTERED')['regime_context']['label']='WRONG'
        rehash(ledger)
        with self.assertRaises(ValueError):audit(ledger)
