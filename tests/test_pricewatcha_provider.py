import unittest
from bot.providers.pricewatcha import PricewatchaProvider

class PricewatchaProviderTests(unittest.TestCase):
    def test_normalizes_search_rows_and_preserves_unknown_condition(self):
        provider=PricewatchaProvider()
        provider._get=lambda url:[{
            "product_id":"prod_123","name":"Example headphones","shop":"Merchant",
            "product_url":"https://merchant.example/product","current_price":89.9,
            "currency":"EUR","status":"active","condition":None
        },{
            "product_id":"demo_1","name":"Preview product","shop":"Demo",
            "product_url":"https://demo.example/item","current_price":12,
            "currency":"EUR","status":"active","preview":True
        },{
            "name":"Bad row","product_url":"https://merchant.example/bad","current_price":"not-price"
        }]
        items=provider._search_sync("headphones")
        self.assertEqual(len(items),1)
        self.assertEqual(items[0].source,"pricewatcha")
        self.assertEqual(items[0].price,89.9)
        self.assertIsNone(items[0].condition)
    async def test_empty_query_rejected(self):
        provider=PricewatchaProvider()
        with self.assertRaises(ValueError):
            await provider.search(" ")
if __name__=="__main__": unittest.main()
