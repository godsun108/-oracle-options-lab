import io
import json
import tempfile
import unittest
from datetime import date,datetime
from pathlib import Path
from research.paco_session_collection import sample,session_status
from research.paco_history_archive import archive,windows
from research.tradier_sandbox_execution import Sandbox

class SessionTests(unittest.TestCase):
    def test_calendar_and_dst(self):
        for moment,status in [('2026-10-26T13:35:00+00:00','OPEN'),('2026-11-02T13:35:00+00:00','OUTSIDE_COLLECTION_WINDOW'),
                              ('2026-11-02T14:35:00+00:00','OPEN'),('2026-11-27T18:45:00+00:00','OUTSIDE_COLLECTION_WINDOW'),
                              ('2026-10-24T14:35:00+00:00','NON_SESSION'),('2026-12-25T14:35:00+00:00','NON_SESSION')]:
            with self.subTest(moment=moment):self.assertEqual(session_status(datetime.fromisoformat(moment)),status)
    def test_skipped_never_calls_provider(self):
        r=sample('',now=datetime.fromisoformat('2026-10-24T14:35:00+00:00'),collector=lambda *a,**k:self.fail('provider called'))
        self.assertEqual(r['status'],'SKIPPED')
    def test_recent_is_not_independently_authenticated(self):
        r=sample('fixture',now=datetime.fromisoformat('2026-10-26T13:35:00+00:00'),
                 collector=lambda *a,**k:{'snapshots':[{'contracts':[{'provider_quote_timing':{'both_sides_within_2_seconds':True}}]}]})
        self.assertEqual(r['provider_recent_contracts'],1)
        self.assertFalse(r['independent_quote_freshness_verified'])

class HistoryTests(unittest.TestCase):
    def test_windows_are_bounded_contiguous(self):
        from datetime import timedelta
        chunks=list(windows(date(2026,10,23)))
        self.assertEqual(len(chunks),20)
        self.assertEqual(chunks[0][0],date(1928,1,3))
        self.assertEqual(chunks[-1][1],date(2026,10,23))
        for a,b in zip(chunks,chunks[1:]):self.assertEqual(a[1]+timedelta(days=1),b[0])
    def test_retains_source_receipts_and_no_coverage_claim(self):
        r=archive('fixture',end=date(1928,1,3),fetch=lambda *a:[{'date':'1928-01-03','close':17}])
        self.assertEqual(r['bars'],1);self.assertIn('parsed_payload_text',r['chunks'][0])
        self.assertFalse(r['history_coverage_complete_verified'])
    def test_invalid_duplicate_out_of_range_rows_not_silently_dropped(self):
        for rows in ([{'date':'1928-01-03','close':'NaN'}],[{'date':'1928-01-04','close':17}],
                     [{'date':'1928-01-03','close':17}]*2):
            r=archive('fixture',end=date(1928,1,3),fetch=lambda *a:rows)
            self.assertEqual(r['bars'],0);self.assertEqual(r['chunks'][0]['status'],'FAILED')
    def test_errors_redacted(self):
        def fail(*a):raise OSError('SECRET')
        r=archive('fixture',end=date(1928,1,3),fetch=fail)
        self.assertNotIn('SECRET',str(r))
    def test_missing_token_makes_no_calls(self):
        self.assertEqual(archive('',fetch=lambda *a:self.fail())['status'],'TOKEN_MISSING')

INTENT={'environment':'sandbox','quantity':1,'option_symbol':'SPY261127P00600000','side':'buy_to_open','limit_price':2.0,'intent_id':'test-1'}
class SandboxTests(unittest.TestCase):
    def client(self,*,timeout=False):
        calls=[]
        def transport(req,timeout=25):
            calls.append(req)
            self.assertTrue(req.full_url.startswith('https://sandbox.tradier.com/v1/'))
            if req.full_url.endswith('/user/profile'):r={'profile':{'account':{'account_number':'TEST123'}}}
            elif b'preview=true' in (req.data or b''):r={'order':{'result':True}}
            else:r={'order':{'id':123,'status':'ok'}}
            return io.BytesIO(json.dumps(r).encode())
        return Sandbox('fixture','TEST123',transport=transport),calls
    def test_requires_opt_in_and_rejects_live_intents(self):
        c,calls=self.client()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.submit(INTENT,Path(d)/'j')
            with self.assertRaises(ValueError):c.submit({**INTENT,'environment':'production'},Path(d)/'j',paper_enabled=True)
        self.assertEqual(calls,[])
    def test_preview_before_submission_and_restart_dedupe(self):
        c,calls=self.client()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'j';r=c.submit(INTENT,p,paper_enabled=True)
            self.assertEqual(r['state'],'ACKNOWLEDGED_NOT_FILLED')
            with self.assertRaises(ValueError):c.submit(INTENT,p,paper_enabled=True)
            self.assertEqual(len(calls),3)
            self.assertIn(b'preview=true',calls[1].data)
            self.assertIn(b'preview=false',calls[2].data)
            self.assertNotIn('fixture',p.read_text())
    def test_uncertain_submission_is_not_retried(self):
        c,calls=self.client();original=c.request
        def request(path,data=None):
            if data and data.get('preview')=='false':raise TimeoutError('ambiguous')
            return original(path,data)
        c.request=request
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'j'
            with self.assertRaises(TimeoutError):c.submit(INTENT,p,paper_enabled=True)
            with self.assertRaises(ValueError):c.submit(INTENT,p,paper_enabled=True)
            self.assertIn('SUBMISSION_UNCERTAIN',p.read_text())
    def test_preview_rejection_cannot_submit(self):
        c,calls=self.client();original=c.request
        c.request=lambda path,data=None: {'order':{'result':False}} if data else original(path,data)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.submit(INTENT,Path(d)/'j',paper_enabled=True)
    def test_no_short_option_sales(self):
        c,_=self.client()
        for changes in ({'side':'sell_to_open'},{'quantity':True},{'limit_price':float('nan')},{'limit_price':21}):
            with self.assertRaises(ValueError):c.payload({**INTENT,**changes})
    def test_reconciliation_does_not_confuse_ack_with_fill(self):
        c,_=self.client()
        order={'id':123,'tag':'oq-test-1','option_symbol':INTENT['option_symbol'],'side':'buy_to_open','type':'limit',
               'duration':'day','quantity':1,'exec_quantity':0,'avg_fill_price':0,'status':'open'}
        c.request=lambda *a:{'order':order}
        self.assertFalse(c.reconcile(123,INTENT)['broker_paper_fill_verified'])
        order.update(status='filled',exec_quantity=1,avg_fill_price=1.9)
        r=c.reconcile(123,INTENT)
        self.assertTrue(r['broker_paper_fill_verified']);self.assertFalse(r['live_fill_verified'])
        order['tag']='wrong'
        with self.assertRaises(ValueError):c.reconcile(123,INTENT)
    def test_selling_requires_actual_sandbox_position(self):
        c,_=self.client();original=c.request
        c.request=lambda path,data=None: {'positions':None} if path.endswith('/positions') else original(path,data)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):c.submit({**INTENT,'side':'sell_to_close'},Path(d)/'j',paper_enabled=True)
    def test_concurrent_submission_claims_once(self):
        from concurrent.futures import ThreadPoolExecutor
        c,calls=self.client()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'j'
            def submit():
                try:return c.submit(INTENT,p,paper_enabled=True)['state']
                except ValueError:return 'BLOCKED'
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
            self.assertEqual(sorted(results),['ACKNOWLEDGED_NOT_FILLED','BLOCKED'])
            self.assertEqual(sum(b'preview=false' in (req.data or b'') for req in calls),1)
    def test_redirects_are_never_followed(self):
        from research.tradier_sandbox_execution import NoRedirect
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,302,'',{},'https://api.tradier.com')

if __name__=='__main__':unittest.main()
