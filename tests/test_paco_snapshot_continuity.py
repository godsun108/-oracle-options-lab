import unittest
from research.paco_snapshot_continuity import append

def snap(n):
    return {"status":"COLLECTED","snapshots":[{"sample":n}],"orders_enabled":False,"collected_at":"2026-10-09T00:00:00Z"}

class ContinuityTests(unittest.TestCase):
    def test_append_and_chain(self):
        first=append(None,snap(1),101)
        second=append(first,snap(2),102)
        self.assertEqual(second["runs_recorded"],2)
        self.assertEqual(second["entries"][1]["previous_sha256"],first["head_sha256"])
    def test_duplicate_rejected(self):
        first=append(None,snap(1),101)
        with self.assertRaises(ValueError): append(first,snap(2),101)
    def test_tamper_rejected(self):
        first=append(None,snap(1),101)
        first["entries"][0]["snapshot_count"]=900
        with self.assertRaises(ValueError): append(first,snap(2),102)
    def test_failed_collection_rejected(self):
        with self.assertRaises(ValueError): append(None,{"status":"FAILED","snapshots":[],"orders_enabled":False},101)
    def test_orders_rejected(self):
        with self.assertRaises(ValueError): append(None,{"status":"COLLECTED","snapshots":[1],"orders_enabled":True},101)
