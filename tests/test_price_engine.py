import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bot.price_engine import PriceEngine

class PriceEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.engine=PriceEngine(str(Path(self.tmp.name)/"test.sqlite"))
    def tearDown(self):
        self.tmp.cleanup()
    def test_observation_history(self):
        oid,key=self.engine.record_observation(title="Headphones",price=80,source="test")
        rows=self.engine.history(key)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["id"],oid)
    def test_budget_limits(self):
        self.assertTrue(self.engine.reserve_api_request(daily_request_limit=1,daily_usd_limit=1))
        self.assertFalse(self.engine.reserve_api_request(daily_request_limit=1,daily_usd_limit=1))
    def test_queue_manual_decision(self):
        oid,_=self.engine.record_observation(title="Product",price=50,source="test")
        cid=self.engine.evaluate(oid)
        self.assertEqual(self.engine.candidate(cid)["status"],"pending")
        self.assertTrue(self.engine.review(cid,"approved","manual"))
        self.assertFalse(self.engine.review(cid,"rejected"))
    def test_anomaly_baseline(self):
        for day in range(5,0,-1):
            stamp=(datetime.now(timezone.utc)-timedelta(days=day)).isoformat()
            self.engine.record_observation(title="Mouse",price=100,source="test",observed_at=stamp)
        oid,_=self.engine.record_observation(title="Mouse",price=40,source="test")
        cid=self.engine.evaluate(oid)
        item=self.engine.candidate(cid)
        self.assertEqual(item["baseline_price"],100)
        self.assertGreaterEqual(item["discount_pct"],50)
if __name__=="__main__":
    unittest.main()
