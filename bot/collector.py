"""Manual watchlist collector with separately budgeted DataForSEO and eBay sources.
Candidates enter private Review Queue only. No scheduling or publishing.
"""
from __future__ import annotations
import os
from bot.providers.dataforseo_shopping import DataForSEOShoppingProvider
from bot.providers.ebay_browse import EbayBrowseProvider
from bot.price_engine import PriceEngine
from bot.market_verifier import verify_peers

NEW_VALUES={"new","neuf","brand new","new in box","new with tags"}

class Collector:
    def __init__(self, engine: PriceEngine, provider=None, ebay_provider=None):
        self.engine=engine
        self.provider=provider or DataForSEOShoppingProvider()
        self.ebay_provider=ebay_provider or EbayBrowseProvider()
        self.max_queries=max(1,int(os.getenv("PRICEHUNTER_MAX_QUERIES_PER_SCAN","3")))
        self.daily_requests=max(1,int(os.getenv("PRICEHUNTER_DAILY_REQUEST_LIMIT","5")))
        self.daily_usd=max(0.01,float(os.getenv("PRICEHUNTER_DAILY_BUDGET_USD","1.00")))
        self.task_cost=max(0.0,float(os.getenv("DATAFORSEO_ESTIMATED_TASK_COST_USD","0.001")))
        self.ebay_daily_requests=max(1,int(os.getenv("PRICEHUNTER_EBAY_DAILY_REQUEST_LIMIT","5")))
    async def scan(self, queries):
        summary={"queries":0,"ebay_queries":0,"results":0,"accepted_new":0,"queued":0,"rejected_not_new":0,"errors":[]}
        for query in list(queries)[:self.max_queries]:
            offers=[]
            # Existing paid/estimated source; reservation happens before provider request.
            budget=self.engine.budget_status("dataforseo",self.daily_requests,self.daily_usd)
            if budget["allowed"] and self.engine.reserve_api_request("dataforseo",self.task_cost,self.daily_requests,self.daily_usd):
                summary["queries"]+=1
                try: offers.extend(await self.provider.search(query))
                except Exception as exc: summary["errors"].append(f"DataForSEO {query}: {type(exc).__name__}: {exc}")
            else:
                summary["errors"].append("Budget DataForSEO atteint; source ignorée.")
            # eBay Browse has no per-call charge documented here, but local daily call cap still applies.
            if getattr(self.ebay_provider,"configured",False):
                ebay_budget=self.engine.budget_status("ebay_browse",self.ebay_daily_requests,1.0)
                if ebay_budget["allowed"] and self.engine.reserve_api_request("ebay_browse",0.0,self.ebay_daily_requests,1.0):
                    summary["ebay_queries"]+=1
                    try: offers.extend(await self.ebay_provider.search(query))
                    except Exception as exc: summary["errors"].append(f"eBay {query}: {type(exc).__name__}: {exc}")
                else: summary["errors"].append("Budget eBay quotidien atteint; source ignorée.")
            summary["results"]+=len(offers)
            peer_evidence=verify_peers(offers)
            for candidate,peer in zip(offers,peer_evidence):
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
                if self.engine.was_recently_queued(key,price=candidate.price,seller=candidate.seller): continue
                self.engine.evaluate(observation_id,peer_reference=peer["peer_median"],peer_count=peer["peer_count"])
                summary["queued"]+=1
        return summary
