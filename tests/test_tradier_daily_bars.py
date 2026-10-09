import datetime as dt
import unittest
from research.tradier_daily_bars import validate_daily_bars

NOW=dt.datetime(2026,10,8,19,0,tzinfo=dt.timezone.utc)
GOOD={"date":"2026-10-07","open":100,"high":103,"low":99,"close":102}

class TradierDailyBarTests(unittest.TestCase):
    def test_valid_and_sorted(self):
        older=dict(GOOD,date="2026-10-06")
        out=validate_daily_bars([GOOD,older],NOW)
        self.assertEqual([r["time"] for r in out],["2026-10-06","2026-10-07"])
    def test_excludes_incomplete_current_day(self):
        today=dict(GOOD,date="2026-10-08")
        self.assertEqual(len(validate_daily_bars([GOOD,today],NOW)),1)
    def test_rejects_corruption(self):
        bad=[
            [GOOD,GOOD],
            [dict(GOOD,high=90)],
            [dict(GOOD,close=float("nan"))],
            [dict(GOOD,date="2026-10-04")],
            [dict(GOOD,open=-1)],
        ]
        for rows in bad:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    validate_daily_bars(rows,NOW)
if __name__=="__main__":
    unittest.main()
