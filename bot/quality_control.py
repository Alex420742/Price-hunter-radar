"""Automatic quality gate for candidate deals.

This module validates offer data before it can become a Telegram alert.
It does not fetch prices or prove that a retailer will honour an offer.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class QualityStatus(str, Enum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Offer:
    title: str
    price: float
    currency: str
    url: str
    brand: Optional[str] = None
    model: Optional[str] = None
    ean: Optional[str] = None
    seller: Optional[str] = None
    condition: Optional[str] = None
    in_stock: Optional[bool] = None
    shipping_cost: Optional[float] = None
    reference_prices: tuple[float, ...] = ()
    observed_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class QualityReport:
    status: QualityStatus
    score: int
    reasons: tuple[str, ...]
    checks_passed: tuple[str, ...]


SUPPORTED_CURRENCIES = {"EUR", "GBP", "CHF", "PLN", "CZK", "SEK", "DKK", "NOK"}


def assess_offer(offer: Offer, now: Optional[datetime] = None) -> QualityReport:
    """Assess an offer conservatively; missing critical facts never pass silently."""
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    passed: list[str] = []
    score = 100
    rejected = False

    def fail(message: str, penalty: int, critical: bool = False) -> None:
        nonlocal score, rejected
        reasons.append(message)
        score -= penalty
        rejected = rejected or critical

    if not offer.title.strip() or not offer.url.strip():
        fail("Titre ou URL manquant", 100, True)
    else:
        passed.append("Titre et URL présents")

    if offer.price <= 0:
        fail("Prix nul ou négatif", 100, True)
    else:
        passed.append("Prix positif")

    if offer.currency not in SUPPORTED_CURRENCIES:
        fail("Devise absente ou non prise en charge", 35)
    else:
        passed.append("Devise reconnue")

    if not (offer.ean or (offer.brand and offer.model)):
        fail("Identité produit insuffisante : EAN ou marque + modèle requis", 45)
    else:
        passed.append("Identité produit renseignée")

    if not offer.seller:
        fail("Vendeur non identifié", 30)
    else:
        passed.append("Vendeur identifié")

    if offer.condition is None:
        fail("État du produit non confirmé", 25)
    elif offer.condition.strip().lower() not in {"new", "neuf"}:
        fail("Produit non neuf : exclu du radar", 100, True)
    else:
        passed.append("Produit neuf")

    if offer.in_stock is not True:
        fail("Disponibilité en stock non confirmée", 30)
    else:
        passed.append("Stock confirmé")

    if offer.shipping_cost is None or offer.shipping_cost < 0:
        fail("Frais de livraison inconnus ou invalides", 15)
    else:
        passed.append("Frais de livraison renseignés")

    if not offer.source:
        fail("Source de collecte non renseignée", 15)
    else:
        passed.append("Source identifiée")

    if offer.observed_at is None:
        fail("Date/heure d'observation absente", 20)
    else:
        observed = offer.observed_at
        if observed.tzinfo is None:
            fail("Horodatage sans fuseau horaire", 15)
        else:
            age_seconds = (now - observed.astimezone(timezone.utc)).total_seconds()
            if age_seconds < -300:
                fail("Horodatage situé dans le futur", 20)
            elif age_seconds > 6 * 60 * 60:
                fail("Donnée trop ancienne (plus de 6 heures)", 30)
            else:
                passed.append("Donnée récente (moins de 6 heures)")

    valid_refs = [p for p in offer.reference_prices if p > 0]
    if len(valid_refs) >= 2:
        passed.append("Au moins deux prix de référence disponibles")
    elif len(valid_refs) == 1:
        fail("Une seule référence de prix : comparaison insuffisante", 15)
    else:
        fail("Aucun prix de référence indépendant", 25)

    # A very low price is a lead, not proof of an error. Flag extreme deviations
    # for manual verification instead of automatically calling them confirmed.
    if valid_refs and offer.price > 0:
        median_ref = sorted(valid_refs)[len(valid_refs) // 2]
        if offer.price < median_ref * 0.10:
            fail("Prix inférieur à 10 % de la référence : contrôle humain obligatoire", 20)

    score = max(0, min(100, score))
    if rejected or score < 50:
        status = QualityStatus.REJECTED
    elif score < 85 or reasons:
        status = QualityStatus.REVIEW
    else:
        status = QualityStatus.APPROVED

    return QualityReport(status, score, tuple(reasons), tuple(passed))
