"""DataForSEO Google Shopping adapter (async task API).

This adapter is intentionally not wired into the scanner yet. It can submit
keyword tasks and retrieve structured results. Candidates are unverified offers;
condition, stock and shipping must not be inferred unless the provider returned
explicit evidence.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


BASE_URL = "https://api.dataforseo.com/v3/merchant/google/products"


@dataclass(frozen=True)
class ShoppingCandidate:
    title: str
    price: float
    currency: str
    seller: str | None
    product_url: str | None
    source: str
    observed_at: datetime
    product_id: str | None = None
    shipping_cost: float | None = None
    condition: str | None = None
    in_stock: bool | None = None
    old_price: float | None = None
    rating: float | None = None
    review_count: int | None = None


class DataForSEOError(RuntimeError):
    """Raised for provider/API errors, invalid credentials, or malformed responses."""


class DataForSEOShoppingProvider:
    """Keyword-based Google Shopping provider. Normal priority is used by default."""

    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
        *,
        location_name: str = "France",
        language_name: str = "French",
        se_domain: str = "google.fr",
        depth: int = 40,
        timeout: float = 30.0,
    ) -> None:
        self.login = login or os.getenv("DATAFORSEO_LOGIN", "")
        self.password = password or os.getenv("DATAFORSEO_PASSWORD", "")
        self.location_name = location_name
        self.language_name = language_name
        self.se_domain = se_domain
        self.depth = max(1, min(int(depth), 40))
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.login and self.password)

    def _request(self, endpoint: str, payload: Any = None) -> dict[str, Any]:
        if not self.configured:
            raise DataForSEOError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required.")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        token = base64.b64encode(f"{self.login}:{self.password}".encode()).decode()
        req = urllib.request.Request(
            f"https://api.dataforseo.com{endpoint}",
            data=body,
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST" if body is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise DataForSEOError(f"Provider HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise DataForSEOError(f"Provider network error: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataForSEOError("Provider returned invalid JSON.") from exc
        if data.get("status_code") not in (None, 20000):
            raise DataForSEOError(
                f"Provider API error {data.get('status_code')}: {data.get('status_message')}"
            )
        return data

    async def search(self, keyword: str) -> list[ShoppingCandidate]:
        """Search one query; async API tasks are polled with a conservative delay."""
        query = keyword.strip()
        if not query:
            raise ValueError("keyword must not be empty")
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, keyword: str) -> list[ShoppingCandidate]:
        post = self._request(
            "/v3/merchant/google/products/task_post",
            [{
                "keyword": keyword,
                "location_name": self.location_name,
                "language_name": self.language_name,
                "se_domain": self.se_domain,
                "depth": self.depth,
                "priority": 1,
            }],
        )
        tasks = post.get("tasks") or []
        if not tasks or not tasks[0].get("id"):
            raise DataForSEOError("Provider accepted no task ID.")
        task_id = tasks[0]["id"]

        # Provider tasks are asynchronous. Poll gently; avoid tight loops.
        for attempt in range(12):
            if attempt:
                import time
                time.sleep(min(2 + attempt, 15))
            result = self._request(f"/v3/merchant/google/products/task_get/advanced/{task_id}")
            tasks = result.get("tasks") or []
            if not tasks:
                continue
            task = tasks[0]
            if task.get("status_code") == 20000:
                return self._parse_items(task)
            if task.get("status_code") not in (None, 20100, 40601, 40602):
                raise DataForSEOError(
                    f"Task failed {task.get('status_code')}: {task.get('status_message')}"
                )
        raise DataForSEOError("Task did not finish within the polling window.")

    @staticmethod
    def _parse_items(task: dict[str, Any]) -> list[ShoppingCandidate]:
        observed_at = datetime.now(timezone.utc)
        results = task.get("result") or []
        candidates: list[ShoppingCandidate] = []
        for result in results:
            for item in result.get("items") or []:
                if item.get("type") not in (None, "google_shopping_serp"):
                    continue
                price = item.get("price")
                try:
                    price = float(price)
                except (TypeError, ValueError):
                    continue
                if price <= 0:
                    continue
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                delivery = item.get("delivery_price") or {}
                ship = delivery.get("current") if isinstance(delivery, dict) else None
                try:
                    ship = float(ship) if ship is not None else None
                except (TypeError, ValueError):
                    ship = None
                candidates.append(ShoppingCandidate(
                    title=title,
                    price=price,
                    currency=str(item.get("currency") or "EUR"),
                    seller=item.get("seller"),
                    product_url=item.get("url") or item.get("product_url"),
                    source="DataForSEO Google Shopping",
                    observed_at=observed_at,
                    product_id=item.get("product_id") or item.get("data_docid"),
                    shipping_cost=ship,
                    condition=None,  # Google Shopping result does not reliably prove new condition
                    in_stock=None,  # never infer stock from a search snippet
                    old_price=_as_float(item.get("old_price")),
                    rating=_as_float((item.get("rating") or {}).get("value") if isinstance(item.get("rating"), dict) else item.get("rating")),
                    review_count=_as_int(item.get("reviews_count") or item.get("review_count")),
                ))
        return candidates


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
