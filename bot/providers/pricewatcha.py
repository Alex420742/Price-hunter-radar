"""Pricewatcha public product-search API adapter (no API key for read/search).
Treat search catalog as third-party price intelligence, not direct merchant truth.
"""
from __future__ import annotations
import asyncio, json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from bot.providers.dataforseo_shopping import ShoppingCandidate

BASE="https://pricewatcha.com/api/v1"

class PricewatchaError(RuntimeError): pass

class PricewatchaProvider:
    def __init__(self, *, timeout=15, base_url=None):
        self.timeout=timeout
        self.base_url=(base_url or os.getenv("PRICEWATCHA_API_BASE",BASE)).rstrip("/")
        self.enabled=os.getenv("PRICEWATCHA_ENABLED","false").strip().lower() not in {"0","false","no","off"}
    @property
    def configured(self):
        return self.enabled
    def _get(self,url):
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"PriceHunterRadar/0.1"})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as res:
                payload=json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body=exc.read().decode("utf-8",errors="replace")[:300]
            raise PricewatchaError(f"Pricewatcha HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError,TimeoutError) as exc:
            raise PricewatchaError(f"Pricewatcha network error: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise PricewatchaError("Pricewatcha returned invalid JSON") from exc
        return payload
    async def search(self, keyword):
        q=(keyword or "").strip()
        if not q: raise ValueError("keyword must not be empty")
        return await asyncio.to_thread(self._search_sync,q)
    def _search_sync(self,keyword):
        url=self.base_url+"/search?"+urllib.parse.urlencode({"q":keyword[:120],"limit":25})
        payload=self._get(url)
        rows=payload if isinstance(payload,list) else payload.get("products",payload.get("results",[]))
        if not isinstance(rows,list): raise PricewatchaError("Unexpected search response shape")
        out=[]
        for row in rows:
            if not isinstance(row,dict): continue
            name=row.get("name") or row.get("title")
            url=row.get("product_url") or row.get("url")
            shop=row.get("shop") or row.get("merchant") or row.get("platform")
            condition=row.get("condition") or row.get("product_condition")
            try: price=float(row.get("current_price",row.get("price")))
            except (TypeError,ValueError): continue
            if not name or not url or price<=0: continue
            if row.get("preview") is True or row.get("status") not in (None,"active"): continue
            out.append(ShoppingCandidate(
                title=str(name),price=price,currency=str(row.get("currency") or "EUR"),
                seller=str(shop) if shop else None,product_url=str(url),source="pricewatcha",
                observed_at=datetime.now(timezone.utc),product_id=str(row.get("product_id")) if row.get("product_id") else None,
                shipping_cost=None,condition=str(condition) if condition else None,
                in_stock=None,old_price=None,rating=None,review_count=None))
        return out
