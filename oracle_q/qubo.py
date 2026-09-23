"""Oracle Q: dependency-light QUBO portfolio scaffold.

This module intentionally contains no market forecasting. It accepts a fixed
set of candidate positions and converts expected return, covariance, and
linear transaction costs into a binary quadratic objective. Small problems
can be solved exactly to provide a deterministic classical benchmark.
"""
from __future__ import annotations
import itertools
import numpy as np


def utility(x, mu, cov, costs, risk_lambda=1.0, cost_gamma=1.0):
    x=np.asarray(x,dtype=float)
    mu=np.asarray(mu,dtype=float)
    cov=np.asarray(cov,dtype=float)
    costs=np.asarray(costs,dtype=float)
    return float(mu@x-risk_lambda*(x@cov@x)-cost_gamma*(costs@x))


def exact_binary_portfolio(mu, cov, costs, max_positions=None,
                           risk_lambda=1.0, cost_gamma=1.0):
    """Exhaustive classical baseline for small candidate sets."""
    n=len(mu)
    if n>24:
        raise ValueError("Exact baseline intentionally limited to <=24 positions")
    best_x=None; best_u=-np.inf
    for bits in itertools.product((0,1),repeat=n):
        if max_positions is not None and sum(bits)>max_positions:
            continue
        u=utility(bits,mu,cov,costs,risk_lambda,cost_gamma)
        if u>best_u:
            best_u=u; best_x=np.asarray(bits,dtype=int)
    return best_x,best_u


def qubo_matrix(mu, cov, costs, risk_lambda=1.0, cost_gamma=1.0):
    """Return symmetric Q where minimizing x'Qx equals negative utility."""
    mu=np.asarray(mu,dtype=float)
    cov=np.asarray(cov,dtype=float)
    costs=np.asarray(costs,dtype=float)
    q=risk_lambda*cov.copy()
    diag=-mu+cost_gamma*costs
    q[np.diag_indices_from(q)]+=diag
    return q


if __name__=="__main__":
    mu=np.array([0.012,0.009,0.006])
    cov=np.array([[.010,.003,.002],[.003,.008,.001],[.002,.001,.006]])
    costs=np.array([.0015,.0010,.0008])
    x,u=exact_binary_portfolio(mu,cov,costs,max_positions=2,risk_lambda=.5)
    q=qubo_matrix(mu,cov,costs,risk_lambda=.5)
    print("selection",x.tolist(),"utility",round(u,8))
    print("qubo_energy",round(float(x@q@x),8))
