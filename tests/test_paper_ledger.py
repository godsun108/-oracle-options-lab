import json
import tempfile
import unittest
from pathlib import Path
from research.paper_ledger import append_record,evaluate

class LedgerTests(unittest.TestCase):
    def test_append_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ledger.jsonl"
            record={"mode":"HISTORICAL_SIMULATION_ONLY","orders_enabled":False,"result":{"status":"NO_TRADE"}}
            self.assertEqual(append_record(p,record)["status"],"APPENDED")
            self.assertEqual(append_record(p,record)["status"],"DUPLICATE")
            self.assertEqual(len(p.read_text().splitlines()),1)
    def test_reject_unvalidated_plan(self):
        spec={"mode":"HISTORICAL_SIMULATION_ONLY","plan":{"symbol":"SPY","direction":"long","trigger":100,"stop":95,"target":110},"bars":[]}
        self.assertEqual(evaluate(spec)["result"]["reason"],"STRATEGY_NOT_VALIDATED")
    def test_reject_live_mode(self):
        with self.assertRaises(ValueError):
            evaluate({"mode":"LIVE","plan":{},"bars":[]})
if __name__=="__main__":
    unittest.main()
