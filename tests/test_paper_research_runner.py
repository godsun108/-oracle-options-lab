import tempfile
import unittest
from pathlib import Path
from research.paper_research_runner import run

class ResearchRunnerTests(unittest.TestCase):
    def test_multiple_candidates_and_no_trade(self):
        bars=[{"time":"2026-10-01","open":99,"high":101,"low":98,"close":100},
              {"time":"2026-10-02","open":101,"high":111,"low":99,"close":110}]
        manifest={"mode":"HISTORICAL_SIMULATION_ONLY","candidates":[
            {"strategy_id":"a-v1","dataset_id":"fixture-v1","plan":{"symbol":"SPY","direction":"long","trigger":100,"stop":95,"target":110,"validated":True},"bars":bars},
            {"strategy_id":"b-v1","dataset_id":"fixture-v1","plan":{"symbol":"GLD","direction":"long","trigger":100,"stop":95,"target":110},"bars":bars}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ledger.jsonl"
            result=run(manifest,p)
            self.assertEqual(result["evaluated"],2)
            self.assertEqual(result["results"][0]["result"]["status"],"CLOSED")
            self.assertEqual(result["results"][1]["result"]["status"],"NO_TRADE")
            self.assertEqual(len(p.read_text().splitlines()),2)
            again=run(manifest,p)
            self.assertTrue(all(r["receipt"]["status"]=="DUPLICATE" for r in again["results"]))
            self.assertFalse(result["orders_enabled"])
    def test_reject_live(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run({"mode":"LIVE","candidates":[]},Path(d)/"ledger")
if __name__=="__main__":
    unittest.main()
