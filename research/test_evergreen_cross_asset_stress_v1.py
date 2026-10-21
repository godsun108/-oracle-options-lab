import unittest
from evergreen_cross_asset_stress_v1 import evaluate

def snapshot():
 return {"mode":"RESEARCH_ONLY","ordersEnabled":False,"equity":2000,
 "positions":[{"riskGroup":"USD","side":"LONG","notional":300},
              {"riskGroup":"USD","side":"LONG","notional":200},
              {"riskGroup":"GOLD","side":"SHORT","notional":100}]}
class StressTests(unittest.TestCase):
 def test_correlated_usd_loss_aggregates(self):
  r=evaluate(snapshot(),[{"id":"shock","groupShocks":{"USD":-.1,"GOLD":.05}}])
  self.assertAlmostEqual(r["results"][0]["hypotheticalPnl"],-55)
  self.assertAlmostEqual(r["worstHypotheticalLossFraction"],.0275)
  self.assertFalse(r["liveOrderAuthorized"])
 def test_opposing_positions_offset(self):
  s=snapshot();s["positions"].append({"riskGroup":"USD","side":"SHORT","notional":100})
  r=evaluate(s,[{"id":"shock","groupShocks":{"USD":-.1,"GOLD":0}}])
  self.assertAlmostEqual(r["results"][0]["hypotheticalPnl"],-40)
 def test_missing_shock_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"missing group shock"):
   evaluate(snapshot(),[{"id":"bad","groupShocks":{"USD":-.1}}])
 def test_invalid_shock_rejected(self):
  with self.assertRaisesRegex(ValueError,"invalid shock"):
   evaluate(snapshot(),[{"id":"bad","groupShocks":{"USD":float("nan"),"GOLD":0}}])
 def test_live_mode_refused(self):
  s=snapshot();s["ordersEnabled"]=True
  with self.assertRaisesRegex(ValueError,"unsafe"):evaluate(s,[{"id":"x","groupShocks":{}}])
 def test_zero_equity_refused(self):
  s=snapshot();s["equity"]=0
  with self.assertRaisesRegex(ValueError,"equity"):evaluate(s,[{"id":"x","groupShocks":{}}])
if __name__=="__main__":unittest.main()
