import tempfile
import unittest
from pathlib import Path
from research.dispatch_outbox import queue_event,delivery_status

class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.event={"id":"o1","symbol":"SPY","event":"ACTION_REQUIRED","expires_at":"2026-10-08T15:05:00Z"}
    def test_dedupe_and_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"outbox.json"
            self.assertEqual(queue_event(p,self.event,"2026-10-08T15:00:00Z")["status"],"PENDING")
            self.assertEqual(queue_event(p,self.event,"2026-10-08T15:00:00Z")["status"],"DUPLICATE")
            status=delivery_status(p,"o1:ACTION_REQUIRED","2026-10-08T15:06:00Z")
            self.assertTrue(status["late"])
            self.assertFalse(status["actionable"])
    def test_late_enqueue(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"outbox.json"
            self.assertEqual(queue_event(p,self.event,"2026-10-08T15:06:00Z")["status"],"EXPIRED_BEFORE_QUEUE")
    def test_no_provider_claim(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"outbox.json"
            queue_event(p,self.event,"2026-10-08T15:00:00Z")
            self.assertFalse(delivery_status(p,"o1:ACTION_REQUIRED","2026-10-08T15:01:00Z")["actionable"])
if __name__=="__main__":
    unittest.main()
