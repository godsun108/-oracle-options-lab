import unittest
from research.forward_paper import initial_state,step
from research.conditional_paper import Plan

def bar(t,o,h,l,c):
    return {"time":t,"open":o,"high":h,"low":l,"close":c}

class ForwardPaperTests(unittest.TestCase):
    def setUp(self):
        self.plan=Plan("SPY","long",100,95,110,validated=True)
    def test_signal_then_next_open_and_exit(self):
        s=initial_state(2000)
        s=step(s,self.plan,bar("1",99,101,98,100))
        self.assertIsNone(s["position"])
        self.assertIsNotNone(s["pending"])
        s=step(s,self.plan,bar("2",101,111,99,110))
        self.assertIsNone(s["position"])
        self.assertEqual([e["type"] for e in s["events"][:3]],["PAPER_SIGNAL","PAPER_ENTRY","PAPER_EXIT"])
        self.assertEqual(s["events"][2]["reason"],"TARGET")
        self.assertFalse(s["orders_enabled"])
    def test_duplicate_rejected(self):
        s=step(initial_state(),self.plan,bar("1",99,100,98,99))
        with self.assertRaises(ValueError):
            step(s,self.plan,bar("1",99,100,98,99))
    def test_unvalidated_rejected(self):
        with self.assertRaises(ValueError):
            step(initial_state(),Plan("SPY","long",100,95,110),bar("1",99,100,98,99))
    def test_short_not_executed(self):
        p=Plan("SPY","short",100,105,90,validated=True)
        s=step(initial_state(),p,bar("1",101,102,99,100))
        self.assertIsNone(s["position"])
if __name__=="__main__":
    unittest.main()
