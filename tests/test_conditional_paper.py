import unittest
from research.conditional_paper import Plan, simulate

def bar(day, o, h, l, c):
    return {"time":day,"open":o,"high":h,"low":l,"close":c}

class PaperEngineTests(unittest.TestCase):
    def test_no_validation_no_trade(self):
        plan=Plan("SPY","long",100,95,110)
        self.assertEqual(simulate(plan,[bar("1",99,100,98,100),bar("2",101,102,99,101)])["status"],"NO_TRADE")
    def test_no_lookahead(self):
        plan=Plan("SPY","long",100,95,110,validated=True)
        result=simulate(plan,[bar("1",99,101,98,100),bar("2",101,111,99,110)])
        self.assertEqual(result["entry_time"],"2")
        self.assertEqual(result["exit_reason"],"TARGET")
    def test_stop_wins_ambiguous_bar(self):
        plan=Plan("SPY","long",100,95,110,validated=True)
        result=simulate(plan,[bar("1",99,101,98,100),bar("2",101,112,94,100)])
        self.assertEqual(result["exit_reason"],"STOP")
        self.assertLess(result["pnl"],0)
    def test_no_trigger(self):
        plan=Plan("GLD","long",100,95,110,validated=True)
        self.assertEqual(simulate(plan,[bar("1",90,92,89,91),bar("2",91,92,90,91)])["status"],"NO_TRADE")
    def test_invalid_levels(self):
        with self.assertRaises(ValueError):
            simulate(Plan("SPY","long",100,105,110,validated=True),[])
    def test_duplicate_bars(self):
        with self.assertRaises(ValueError):
            simulate(Plan("SPY","long",100,95,110,validated=True),[bar("1",99,101,98,100)]*2)
if __name__=="__main__":
    unittest.main()
