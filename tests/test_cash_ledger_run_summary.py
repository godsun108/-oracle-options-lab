import unittest
from research.cash_observation_ledger import append
from research.cash_ledger_run_summary import summarize
from tests.test_cash_observation_ledger import baseline

class SummaryTests(unittest.TestCase):
    def test_checkpoint_count_and_proof(self):
        ledger=append(append(None,baseline()),baseline("2026-10-09","b"*64))
        text=summarize(ledger)
        self.assertIn("Checkpoints: **2**",text)
        self.assertIn("2026-10-09",text)
        self.assertIn("not evidence of trading profitability",text)
    def test_reject_tampered_chain(self):
        ledger=append(None,baseline())
        ledger["entries"][0]["cash"]=3000
        with self.assertRaises(ValueError):
            summarize(ledger)
if __name__=="__main__":
    unittest.main()
