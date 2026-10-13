import copy
import unittest
from research.edge_history_diagnostic import diagnose


class HistoryDiagnosticTests(unittest.TestCase):
    def report(self):
        return {"schema":"oracle-q-edge-lab-v1","orders_enabled":False,"reports":[{
            "symbol":"IWM","status":"DATA_OR_VALIDATION_FAILURE",
            "diagnostic":{"date":"2025-03-06"},
            "source_evidence":{"rows":[{"date":"2025-03-06","open":"NaN"}]}}]}

    def test_probe_never_replaces_original_or_authorizes_settlement(self):
        source=self.report();before=copy.deepcopy(source);calls=[]
        def fetch(*args):
            calls.append(args)
            return [{"date":"2025-03-06","open":200}]
        result=diagnose(source,"token",fetch=fetch)
        self.assertEqual(source,before)
        self.assertEqual(calls,[("IWM","token","2025-03-06","2025-03-06")])
        self.assertEqual(result["results"][0]["status"],"SINGLE_DATE_OPEN_VALID_BROAD_RESPONSE_INVALID")
        self.assertFalse(result["usable_for_forward_settlement"])
        self.assertEqual(result["results"][0]["original_row"]["open"],"NaN")

    def test_failed_probe_not_retried_and_exception_text_not_disclosed(self):
        calls=[]
        def fetch(*args):calls.append(1);raise TimeoutError("SECRET")
        result=diagnose(self.report(),"token",fetch=fetch)
        self.assertEqual(len(calls),1)
        self.assertEqual(result["results"][0]["status"],"PROBE_FAILED")
        self.assertNotIn("SECRET",str(result))

    def test_duplicate_markets_rejected_before_requests(self):
        source=self.report();source["reports"]*=2
        with self.assertRaises(ValueError):
            diagnose(source,"token",fetch=lambda *args:self.fail("must not fetch"))

    def test_invalid_probe_remains_invalid(self):
        result=diagnose(self.report(),"token",fetch=lambda *args:[])
        self.assertEqual(result["results"][0]["status"],"SINGLE_DATE_OPEN_UNAVAILABLE_OR_INVALID")


if __name__=="__main__":unittest.main()
