import datetime as dt
import tempfile
import unittest
from pathlib import Path
from research.tradier_paper_bridge import paper_from_tradier

NOW=dt.datetime(2026,10,8,21,0,tzinfo=dt.timezone.utc)
PLAN={"symbol":"SPY","direction":"long","trigger":100,"stop":95,"target":110,"validated":True}
ROWS=[
    {"date":"2026-10-06","open":99,"high":101,"low":98,"close":100},
    {"date":"2026-10-07","open":101,"high":111,"low":99,"close":110},
]
class TradierPaperBridgeTests(unittest.TestCase):
    def test_initial_and_replay_paper_only(self):
        def fetch(symbol,token,start,end):
            self.assertEqual(symbol,"SPY")
            return ROWS
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            first=paper_from_tradier(PLAN,"dummy",path,NOW,fetch)
            self.assertEqual(first["accepted_bars"],2)
            self.assertFalse(first["orders_enabled"])
            self.assertEqual(first["last_bar"],"2026-10-07")
            replay=paper_from_tradier(PLAN,"dummy",path,NOW,fetch)
            self.assertEqual(replay["accepted_bars"],0)
    def test_reject_bad_input_before_state_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            with self.assertRaises(ValueError):
                paper_from_tradier(dict(PLAN,validated=False),"dummy",path,NOW,lambda *args: ROWS)
            with self.assertRaises(ValueError):
                paper_from_tradier(PLAN,"dummy",path,NOW,lambda *args: [dict(ROWS[0],high=1)])
            self.assertFalse(path.exists())
if __name__=="__main__":
    unittest.main()
