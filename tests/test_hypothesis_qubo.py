import unittest
import numpy as np
from oracle_q.hypothesis_qubo import anneal_schedule, exact_schedule, qubo_for_scheduler


def candidates(n=8):
    return [{"id": str(i), "option_structure": str(i%3), "signal_family": str(i%2),
             "regime": "trend", "target": "research", "contract_features": False,
             "information_value": 1+i*.03, "complexity": 1+i%2} for i in range(n)]


class HypothesisSchedulerTests(unittest.TestCase):
    def test_annealing_objective_matches_qubo_and_exact_bound(self):
        menu=candidates()
        selected,value=anneal_schedule(menu,batch_size=3,steps=1500,incremental=True)
        _,optimum=exact_schedule(menu,batch_size=3)
        x=np.array([int(c in selected) for c in menu])
        self.assertAlmostEqual(value,-float(x@qubo_for_scheduler(menu)@x),places=10)
        self.assertLessEqual(value,optimum+1e-10)
        self.assertAlmostEqual(value,optimum,places=10)
        self.assertEqual((selected,value),anneal_schedule(menu,batch_size=3,steps=1500,incremental=True))

    def test_empty_and_full_budgets(self):
        menu=candidates()
        self.assertEqual(anneal_schedule(menu,batch_size=0),([],0.0))
        self.assertEqual(len(anneal_schedule(menu,batch_size=len(menu))[0]),len(menu))

    def test_bad_inputs_fail_explicitly(self):
        for size in (-1,9,True):
            with self.assertRaises(ValueError):
                anneal_schedule(candidates(),batch_size=size)
        bad=candidates();bad[0]["information_value"]=float("nan")
        with self.assertRaises(ValueError):anneal_schedule(bad,batch_size=3)
        bad=candidates();bad[0]["id"]=bad[1]["id"]
        with self.assertRaises(ValueError):exact_schedule(bad,batch_size=3)
        with self.assertRaisesRegex(ValueError,"budget"):
            exact_schedule(candidates(30),batch_size=15)


if __name__=="__main__":unittest.main()
