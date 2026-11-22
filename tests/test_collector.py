import unittest
from datetime import datetime, timezone
from bot.collector import Collector
from bot.price_engine import PriceEngine
import tempfile, os

class FakeProvider:
    configured=True
    def __init__(self, items): self.items=items; self.calls=0
    async def search(self, query):
        self.calls+=1
        return self.items

class Candidate:
    def __init__(self, title, price, condition, seller="Seller"):
        self.title=title; self.price=price; self.condition=condition; self.seller=seller
        self.currency="EUR"; self.product_url="https://example.test/product"; self.source="mock"
        self.shipping_cost=None; self.in_stock=None; self.product_id=title; self.observed_at=datetime.now(timezone.utc)

class CollectorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.engine=PriceEngine(os.path.join(self.tmp.name,"test.sqlite"))
    def tearDown(self): self.tmp.cleanup()
    async def test_only_explicit_new_condition_is_queued(self):
        provider=FakeProvider([Candidate("New item",49,"new"),Candidate("Unknown item",35,None),Candidate("Used",20,"used")])
        collector=Collector(self.engine,provider)
        collector.max_queries=1
        result=await collector.scan(["query"])
        self.assertEqual(result["results"],3)
        self.assertEqual(result["accepted_new"],1)
        self.assertEqual(result["rejected_not_new"],2)
        self.assertEqual(result["queued"],1)
        self.assertEqual(len(self.engine.list_review("pending")),1)
    async def test_budget_prevents_provider_call(self):
        provider=FakeProvider([Candidate("Item",5,"new")])
        collector=Collector(self.engine,provider)
        collector.daily_requests=0
        result=await collector.scan(["query"])
        self.assertEqual(provider.calls,0)
        self.assertEqual(result["queries"],0)
    async def test_duplicate_candidate_not_queued_twice(self):
        provider=FakeProvider([Candidate("Repeat",99,"neuf")])
        collector=Collector(self.engine,provider)
        collector.max_queries=1
        await collector.scan(["first"])
        await collector.scan(["second"])
        self.assertEqual(len(self.engine.list_review("pending")),1)

if __name__=="__main__": unittest.main()
