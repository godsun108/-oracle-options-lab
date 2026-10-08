import tempfile
import unittest
from pathlib import Path
from research.persistent_forward_runner import run

class PersistentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.plan={"symbol":"SPY","direction":"long","trigger":100,"stop":95,
                   "target":110,"validated":True}
        self.bars=[
            {"time":"2026-10-01","open":99,"high":101,"low":98,"close":100},
            {"time":"2026-10-02","open":101,"high":111,"low":99,"close":110}]
    def test_restart_no_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            first=run(self.plan,self.bars[:1],path)
            self.assertEqual(first["accepted_bars"],1)
            second=run(self.plan,self.bars,path)
            self.assertEqual(second["accepted_bars"],1)
            self.assertEqual(second["event_count"],3)
            third=run(self.plan,self.bars,path)
            self.assertEqual(third["accepted_bars"],0)
            self.assertEqual(third["event_count"],3)
            self.assertFalse(third["orders_enabled"])
    def test_no_rearm_on_exit_bar(self):
        with tempfile.TemporaryDirectory() as d:
            result=run(self.plan,self.bars,Path(d)/"state.json")
            self.assertEqual(result["event_count"],3)
            self.assertIsNone(result["open_position"])
    def test_plan_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            run(self.plan,self.bars[:1],path)
            with self.assertRaises(ValueError):
                run({**self.plan,"trigger":101},self.bars,path)
    def test_corrupt_snapshot_refuses_resume(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            run(self.plan,self.bars[:1],path)
            import json
            envelope=json.loads(path.read_text())
            envelope["payload"]["state"]["cash"]=999999
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError):
                run(self.plan,self.bars,path)
    def test_unvalidated_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run({**self.plan,"validated":False},self.bars,Path(d)/"state")
if __name__=="__main__":
    unittest.main()
