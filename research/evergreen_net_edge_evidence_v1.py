"""Fail-closed net trading edge evidence from independently sourced settled trades.

A reported paper ledger is NOT an authenticated broker ledger. Results are
descriptive and can never authorize trading or strategy promotion.
"""
import math,statistics
def _num(x,name):
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
  raise ValueError("invalid "+name)
 return float(x)
def evaluate(packet):
 if not isinstance(packet,dict) or packet.get("schema")!="oracle.settled-trades.v1":
  raise ValueError("invalid settled trade packet")
 if packet.get("mode")!="RESEARCH_ONLY" or packet.get("ordersEnabled") is not False:
  raise ValueError("live execution prohibited")
 trades=packet.get("trades")
 if not isinstance(trades,list):raise ValueError("invalid trades")
 ids=set();total=0.;bench=0.;wins=0;costs=0.;net=[];benchmarks_complete=True
 for t in trades:
  if not isinstance(t,dict) or not isinstance(t.get("id"),str) or not t["id"] or t["id"] in ids:
   raise ValueError("duplicate or invalid trade")
  ids.add(t["id"])
  gross=_num(t.get("grossPnl"),"gross PnL")
  fees=_num(t.get("fees"),"fees")
  slippage=_num(t.get("slippageCost"),"slippage")
  benchmark_raw=t.get("benchmarkPnl")
  if benchmark_raw is None:
   benchmarks_complete=False
   benchmark=0.
  else:
   benchmark=_num(benchmark_raw,"benchmark PnL")
  if fees<0 or slippage<0:raise ValueError("negative costs")
  pnl=gross-fees-slippage
  net.append(pnl);total+=pnl;bench+=benchmark;costs+=fees+slippage
  wins+=pnl>0
 count=len(net)
 return {"schema":"oracle.evergreen-net-edge-evidence.v1","mode":"RESEARCH_ONLY",
  "settledTradeCount":count,"reportedNetPnl":total,"reportedBenchmarkPnl":bench,
  "reportedExcessPnl":total-bench if count and benchmarks_complete else None,
  "benchmarkCoverageComplete":bool(count and benchmarks_complete),"reportedCosts":costs,
  "reportedWinRate":wins/count if count else None,
  "reportedMeanNetPnl":statistics.mean(net) if count else None,
  "netPositive":total>0 if count else None,
  "independentLedgerVerified":False,"independentBenchmarkVerified":False,
  "edgeEstablished":False,"promotionAuthorized":False,"paperCandidateEligible":False,
  "liveOrderAuthorized":False,"ordersEnabled":False,
  "reasons":["no_settled_trades"] if not count else ["independent_settlement_and_benchmark_verification_missing"]+([] if benchmarks_complete else ["benchmark_missing"]),
  "warning":"Reported values only; requires independently reconciled settlements, matched benchmark, costs and sufficient forward observations."}
