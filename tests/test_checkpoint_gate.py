import tempfile
import unittest
from pathlib import Path
from research.checkpoint_gate import validate_checkpoint
from research.paper_state_snapshot import write_snapshot
from research.forward_paper import initial_state

class CheckpointGateTests(unittest.TestCase):
    def test_matching_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state.json"
            plan={"symbol":"TEST"}
            state=initial_state()
            state["last_bar"]="fixture-00000002"
            write_snapshot(p,plan,state)
            report={"last_bar":"fixture-00000002","mode":"FORWARD_PAPER_ONLY","orders_enabled":False}
            self.assertEqual(validate_checkpoint(p,plan,report)["last_bar"],"fixture-00000002")
            for changed in [
                dict(report,last_bar="fixture-00000004"),
                dict(report,orders_enabled=True),
                dict(report,mode="LIVE"),
                dict(report,last_bar=None),
            ]:
                with self.assertRaises(ValueError):
                    validate_checkpoint(p,plan,changed)
            with self.assertRaises(ValueError):
                validate_checkpoint(p,{"symbol":"WRONG"},report)
if __name__=="__main__":
    unittest.main()
