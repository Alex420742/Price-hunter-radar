import unittest
from datetime import datetime, timezone
from bot.market_verifier import verify_peers

class Candidate:
    def __init__(self,title,price,url):
        self.title=title; self.price=price; self.product_url=url

class MarketVerifierTests(unittest.TestCase):
    def test_same_product_peer_prices_across_domains(self):
        items=[
            Candidate("Sony WH-1000XM5 headphones",250,"https://shop-one.example/item"),
            Candidate("Sony WH-1000XM5 wireless headphones",220,"https://shop-two.example/item"),
            Candidate("Sony WH 1000 XM5 headphones",210,"https://shop-three.example/item"),
        ]
        result=verify_peers(items)
        self.assertEqual(result[0]["peer_count"],2)
        self.assertEqual(result[0]["peer_median"],215)
    def test_same_domain_is_not_independent_peer(self):
        items=[
            Candidate("Sony WH-1000XM5",250,"https://shop.example/a"),
            Candidate("Sony WH-1000XM5",220,"https://www.shop.example/b"),
        ]
        self.assertEqual(verify_peers(items)[0]["peer_count"],0)
if __name__=="__main__": unittest.main()
