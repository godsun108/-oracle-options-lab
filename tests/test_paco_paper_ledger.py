import unittest
from research.paco_paper_ledger import initial,record,verify

Q={"bid":1.3,"ask":1.35,"age_seconds":0.1,"bid_size":10,"ask_size":10}
T1="2026-10-09T09:30:01-04:00"
T2="2026-10-09T09:30:02-04:00"
class PACOLedgerTests(unittest.TestCase):
    def test_buy_sell_and_verify(self):
        a=record(initial(),symbol="SPY_TEST",side="BUY",quantity=2,quote=Q,as_of=T1)
        b=record(a,symbol="SPY_TEST",side="SELL",quantity=1,quote=Q,as_of=T2)
        self.assertEqual(b["positions"],{"SPY_TEST":1})
        self.assertTrue(verify(b)["verified"])
        self.assertFalse(verify(b)["performance_established"])
    def test_no_unheld_sell(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="SELL",quantity=1,quote=Q,as_of=T1)
    def test_no_fake_size(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="BUY",quantity=11,quote=Q,as_of=T1)
    def test_no_overspending(self):
        with self.assertRaises(ValueError):
            record(initial(100),symbol="SPY_TEST",side="BUY",quantity=1,quote=Q,as_of=T1)
    def test_tamper_detected(self):
        a=record(initial(),symbol="SPY_TEST",side="BUY",quantity=1,quote=Q,as_of=T1)
        a["entries"][0]["price"]=0.01
        with self.assertRaises(ValueError):verify(a)
    def test_stale_quote_rejected(self):
        with self.assertRaises(ValueError):
            record(initial(),symbol="SPY_TEST",side="BUY",quantity=1,
                   quote={**Q,"age_seconds":30},as_of=T1)

class PACOLedgerIntegrityTests(unittest.TestCase):
    def buy(self, **kwargs):
        return record(initial(),symbol='SPY_TEST',side='BUY',quantity=1,quote=Q,as_of=T1,**kwargs)

    def test_append_rejects_corrupt_prior_cash(self):
        a=self.buy();a['cash']+=1000
        with self.assertRaisesRegex(ValueError,'state mismatch'):
            record(a,symbol='SPY_TEST',side='BUY',quantity=1,quote=Q,as_of=T2)

    def test_timezone_offsets_compare_instants_not_text(self):
        a=record(initial(),symbol='SPY_TEST',side='BUY',quantity=1,quote=Q,
                 as_of='2026-10-09T13:30:01+00:00')
        b=record(a,symbol='SPY_TEST',side='SELL',quantity=1,quote=Q,as_of=T2)
        self.assertTrue(verify(b)['verified'])
        with self.assertRaisesRegex(ValueError,'nonmonotonic'):
            record(a,symbol='SPY_TEST',side='SELL',quantity=1,quote=Q,
                   as_of='2026-10-09T14:00:00+01:00')

    def test_quote_retained_and_rehashed_wrong_price_rejected(self):
        from research.paco_paper_ledger import _hash
        a=self.buy();self.assertEqual(a['entries'][0]['quote_evidence'],Q)
        e=a['entries'][0];e['price']=.01
        e['entry_hash']=_hash({k:v for k,v in e.items() if k!='entry_hash'})
        a['head_hash']=e['entry_hash'];a['cash']=1998.35
        with self.assertRaisesRegex(ValueError,'disagrees with quote'):verify(a)

    def test_zero_bid_exit_and_fees_reconcile(self):
        a=self.buy();b=record(a,symbol='SPY_TEST',side='SELL',quantity=1,
                             quote={**Q,'bid':0},as_of=T2)
        self.assertTrue(verify(b)['verified'])
        self.assertEqual(b['positions'],{})
        self.assertAlmostEqual(b['cash'],1863.70)

    def test_false_freshness_and_fractional_size_rejected(self):
        for quote in ({**Q,'ask_size':1.9},{**Q,'ask_size':True},
                      {**Q,'provider_timestamp':'2026-10-09T09:00:00-04:00'}):
            with self.assertRaises(ValueError):
                record(initial(),symbol='SPY_TEST',side='BUY',quantity=1,quote=quote,as_of=T1)

    def test_nonfinite_fields_and_false_simulation_rejected(self):
        for fee in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):self.buy(fee_per_contract=fee)
        a=self.buy();a['simulation_only']=False
        with self.assertRaises(ValueError):verify(a)

    def test_legacy_entries_not_relabelled_quote_verified(self):
        from research.paco_paper_ledger import _hash
        a=self.buy();e=a['entries'][0];del e['quote_evidence']
        e['entry_hash']=_hash({k:v for k,v in e.items() if k!='entry_hash'})
        a['head_hash']=e['entry_hash'];v=verify(a)
        self.assertEqual(v['legacy_entries_without_quote_evidence'],1)
        self.assertFalse(v['independent_quote_freshness_verified'])

if __name__=="__main__":unittest.main()
