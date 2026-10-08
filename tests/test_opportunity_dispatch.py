import unittest
from research.opportunity_dispatch import transition,notification

class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.p={"id":"s-1","symbol":"SPY","state":"WATCH","expires_at":"2026-10-08T15:05:00Z"}
    def test_ready_and_notification(self):
        r=transition(self.p,"trigger","2026-10-08T15:00:00Z")
        self.assertEqual(r["event"],"ACTION_REQUIRED")
        self.assertEqual(notification(r)["delivery_status"],"NOT_SENT")
        self.assertFalse(r["orders_enabled"])
    def test_expired_no_approval(self):
        p={**self.p,"state":"READY"}
        r=transition(p,"approve","2026-10-08T15:05:00Z",True,True)
        self.assertEqual(r["opportunity"]["state"],"EXPIRED")
        self.assertEqual(notification(r)["event"],"MISSED_OR_EXPIRED")
    def test_approval_requires_checks(self):
        p={**self.p,"state":"READY"}
        self.assertEqual(transition(p,"approve","2026-10-08T15:01:00Z")["event"],"APPROVAL_BLOCKED_RECHECK")
        r=transition(p,"approve","2026-10-08T15:01:00Z",True,True)
        self.assertEqual(r["event"],"APPROVAL_REQUESTED_NOT_EXECUTED")
        self.assertFalse(r["orders_enabled"])
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            transition(self.p,"trigger","2026-10-08T15:00:00")
if __name__=="__main__":
    unittest.main()
