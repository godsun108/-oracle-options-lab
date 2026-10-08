import unittest
from research.paper_state_snapshot import seal,verify
from research.forward_paper import initial_state

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.plan={"symbol":"SPY","validated":True}
        self.state=initial_state()
    def test_round_trip(self):
        self.assertEqual(verify(seal(self.plan,self.state),self.plan),self.state)
    def test_tampering_rejected(self):
        envelope=seal(self.plan,self.state)
        envelope["payload"]["state"]["cash"]=999999
        with self.assertRaises(ValueError):
            verify(envelope,self.plan)
    def test_wrong_plan_rejected(self):
        with self.assertRaises(ValueError):
            verify(seal(self.plan,self.state),{"symbol":"QQQ","validated":True})
    def test_live_mode_rejected(self):
        with self.assertRaises(ValueError):
            seal(self.plan,{**self.state,"orders_enabled":True})
if __name__=="__main__":
    unittest.main()
