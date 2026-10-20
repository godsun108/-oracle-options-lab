"""Public CI relay smoke test. Synthetic values only; no private imports."""
import hashlib
import json
import unittest

class PublicRelaySmoke(unittest.TestCase):
    def test_canonical_fixture_hash(self):
        fixture = {"mode": "RESEARCH_ONLY", "orders_enabled": False,
                   "synthetic_equity": [2000, 2001, 1999]}
        raw = json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(len(digest), 64)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_synthetic_equity_arithmetic(self):
        equity = [2000, 2001, 1999]
        self.assertAlmostEqual(equity[-1] / equity[0] - 1, -0.0005)

    def test_safety_invariants(self):
        fixture = {"mode": "RESEARCH_ONLY", "orders_enabled": False,
                   "broker_fills_verified": False, "promotion_authorized": False}
        self.assertFalse(any(fixture[k] for k in
                             ("orders_enabled", "broker_fills_verified", "promotion_authorized")))

if __name__ == "__main__":
    unittest.main()
