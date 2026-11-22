import unittest
from datetime import timezone

from bot.providers.dataforseo_shopping import DataForSEOShoppingProvider


class DataForSEOParsingTests(unittest.TestCase):
    def test_parses_valid_shopping_items_and_ignores_invalid_prices(self):
        task = {
            "result": [{
                "items": [
                    {
                        "type": "google_shopping_serp",
                        "title": "Sony WH-1000XM5",
                        "price": 299.99,
                        "currency": "EUR",
                        "seller": "Example Store",
                        "url": "https://example.test/item",
                        "product_id": "123",
                        "old_price": 399.99,
                        "rating": {"value": 4.8},
                        "reviews_count": 500,
                    },
                    {"type": "google_shopping_serp", "title": "Broken", "price": "N/A"},
                    {"type": "google_shopping_serp", "title": "", "price": 15},
                ]
            }]
        }
        candidates = DataForSEOShoppingProvider._parse_items(task)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.title, "Sony WH-1000XM5")
        self.assertEqual(candidate.price, 299.99)
        self.assertEqual(candidate.currency, "EUR")
        self.assertEqual(candidate.seller, "Example Store")
        self.assertEqual(candidate.product_url, "https://example.test/item")
        self.assertEqual(candidate.old_price, 399.99)
        self.assertEqual(candidate.rating, 4.8)
        self.assertEqual(candidate.review_count, 500)
        self.assertIsNone(candidate.condition)
        self.assertIsNone(candidate.in_stock)
        self.assertEqual(candidate.observed_at.tzinfo, timezone.utc)

    def test_empty_keyword_rejected(self):
        provider = DataForSEOShoppingProvider(login="a", password="b")
        with self.assertRaises(ValueError):
            import asyncio
            asyncio.run(provider.search("  "))

    def test_unconfigured_provider_reports_not_configured(self):
        provider = DataForSEOShoppingProvider(login="", password="")
        self.assertFalse(provider.configured)


if __name__ == "__main__":
    unittest.main()
