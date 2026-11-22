"""Manual watchlist collector: provider -> price engine -> private review queue.
No background scheduling or publishing is performed here.
"""
from __future__ import annotations
import os
from dataclasses import asdict
from bot.providers.dataforseo_shopping import DataForSEOShoppingProvider
from bot.price_engine import PriceEngine

NEW_VALUES={"new","neuf","brand new","new in box"}

class Collector:
    def __init__(self, engine: PriceEngine, provider=None):
        self.engine=engine
        self.provider=provider or DataForSEOShoppingProvider()
        self.max_queries=max(1,int(os.getenv("PRICEHUNTER_MAX_QUERIES_PER_SCAN","3")))
        self.daily_requests=max(1,int(os.getenv("PRICEHUNTER_DAILY_REQUEST_LIMIT","5")))
        self.daily_usd=max(0.01,float(os.getenv("PRICEHUNTER_DAILY_BUDGET_USD","1.00")))
        self.task_cost=max(0.0,float(os.getenv("DATAFORSEO_ESTIMATED_TASK_COST_USD","0.001")))
    async def scan(self, queries):
        summary={"queries":0,"results":0,"accepted_new":0,"queued":0,"rejected_not_new":0,"errors":[]}
        for query in list(queries)[:self.max_queries]:
            budget=self.engine.budget_status("dataforseo",self.daily_requests,self.daily_usd)
            if not budget["allowed"]:
                summary["errors"].append("Budget quotidien atteint; collecte arrêtée.")
                break
            if not self.engine.reserve_api_request("dataforseo",self.task_cost,self.daily_requests,self.daily_usd):
                summary["errors"].append("Budget API indisponible; collecte arrêtée.")
                break
            summary["queries"]+=1
            try:
                results=await self.provider.search(query)
            except Exception as exc:
                summary["errors"].append(f"{query}: {type(exc).__name__}: {exc}")
                continue
            summary["results"]+=len(results)
            for candidate in results:
                condition=(candidate.condition or "").strip().lower()
                if condition not in NEW_VALUES:
                    summary["rejected_not_new"]+=1
                    continue
                summary["accepted_new"]+=1
                observation_id,key=self.engine.record_observation(
                    title=candidate.title,price=candidate.price,currency=candidate.currency,
                    seller=candidate.seller,url=candidate.product_url,source=candidate.source,
                    shipping_cost=candidate.shipping_cost,condition=candidate.condition,
                    in_stock=candidate.in_stock,product_id=candidate.product_id,
                    observed_at=candidate.observed_at.isoformat())
                # Deduplication is handled at observation insertion; don't queue repeated candidates.
                if self.engine.was_recently_queued(key,price=candidate.price,seller=candidate.seller):
                    continue
                self.engine.evaluate(observation_id)
                summary["queued"]+=1
        return summary
