import unittest
from research.continuous_fixture import build

class ContinuousFixtureTests(unittest.TestCase):
    def test_distinct_monotonic_batches(self):
        a,b=build(0),build(1)
        self.assertEqual(len(a),2)
        self.assertEqual(len(b),2)
        self.assertLess(a[-1]["time"],b[0]["time"])
    def test_repeat_is_deterministic(self):
        self.assertEqual(build(12),build(12))
    def test_invalid_sequence_rejected(self):
        for n in (-1,100001):
            with self.assertRaises(ValueError):
                build(n)
if __name__=="__main__":
    unittest.main()
