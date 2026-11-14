import unittest
from datetime import datetime, timezone

from bot.quality_control import Offer, QualityStatus, assess_offer


class QualityControlTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 14, 19, 0, tzinfo=timezone.utc)

    def valid_offer(self):
        return Offer(
            title="Samsung Galaxy S26 256 Go",
            price=699.0,
            currency="EUR",
            url="https://shop.example/product",
            brand="Samsung",
            model="Galaxy S26 256 Go",
            seller="Example Retail",
            condition="new",
            in_stock=True,
            shipping_cost=0.0,
            reference_prices=(899.0, 879.0, 849.0),
            observed_at=self.now,
            source="official product feed",
        )

    def test_complete_offer_is_approved(self):
        report = assess_offer(self.valid_offer(), self.now)
        self.assertEqual(report.status, QualityStatus.APPROVED)
        self.assertGreaterEqual(report.score, 85)

    def test_used_item_is_rejected(self):
        offer = self.valid_offer()
        offer = Offer(**{**offer.__dict__, "condition": "used"})
        report = assess_offer(offer, self.now)
        self.assertEqual(report.status, QualityStatus.REJECTED)

    def test_missing_seller_requires_review(self):
        offer = self.valid_offer()
        offer = Offer(**{**offer.__dict__, "seller": None})
        report = assess_offer(offer, self.now)
        self.assertNotEqual(report.status, QualityStatus.APPROVED)
        self.assertTrue(any("Vendeur" in reason for reason in report.reasons))

    def test_missing_stock_is_not_approved(self):
        offer = self.valid_offer()
        offer = Offer(**{**offer.__dict__, "in_stock": None})
        report = assess_offer(offer, self.now)
        self.assertNotEqual(report.status, QualityStatus.APPROVED)

    def test_stale_observation_requires_review(self):
        offer = self.valid_offer()
        old = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
        offer = Offer(**{**offer.__dict__, "observed_at": old})
        report = assess_offer(offer, self.now)
        self.assertNotEqual(report.status, QualityStatus.APPROVED)

    def test_extreme_price_is_never_auto_confirmed(self):
        offer = self.valid_offer()
        offer = Offer(**{**offer.__dict__, "price": 5.0})
        report = assess_offer(offer, self.now)
        self.assertNotEqual(report.status, QualityStatus.APPROVED)
        self.assertTrue(any("10 %" in reason for reason in report.reasons))


if __name__ == "__main__":
    unittest.main()
