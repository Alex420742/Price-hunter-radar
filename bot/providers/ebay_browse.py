"""eBay Browse API search provider. Requires developer OAuth app credentials.
Only queries listings filtered to explicit NEW condition.
"""
from __future__ import annotations
import asyncio, base64, json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from bot.providers.dataforseo_shopping import ShoppingCandidate

TOKEN_URL="https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL="https://api.ebay.com/buy/browse/v1/item_summary/search"

class EbayBrowseError(RuntimeError): pass

class EbayBrowseProvider:
    def __init__(self, client_id=None, client_secret=None, *, marketplace="EBAY_FR", timeout=20):
        self.client_id=client_id or os.getenv("EBAY_CLIENT_ID","")
        self.client_secret=client_secret or os.getenv("EBAY_CLIENT_SECRET","")
        self.marketplace=marketplace
        self.timeout=timeout
        self._token=None
        self._expires_at=0
    @property
    def configured(self):
        return bool(self.client_id and self.client_secret)
    def _request(self,url,headers,data=None):
        req=urllib.request.Request(url,data=data,headers=headers,method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body=exc.read().decode("utf-8",errors="replace")[:400]
            raise EbayBrowseError(f"eBay HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError,TimeoutError) as exc:
            raise EbayBrowseError(f"eBay network error: {exc}") from exc
    def _get_token(self):
        import time
        if self._token and time.time()<self._expires_at-60: return self._token
        if not self.configured: raise EbayBrowseError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required.")
        auth=base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        body=urllib.parse.urlencode({"grant_type":"client_credentials","scope":"https://api.ebay.com/oauth/api_scope"}).encode()
        data=self._request(TOKEN_URL,{"Authorization":"Basic "+auth,"Content-Type":"application/x-www-form-urlencoded"},body)
        if not data.get("access_token"): raise EbayBrowseError("eBay OAuth token missing.")
        self._token=data["access_token"]
        self._expires_at=time.time()+int(data.get("expires_in",7200))
        return self._token
    async def search(self,keyword):
        query=(keyword or "").strip()
        if not query: raise ValueError("keyword must not be empty")
        return await asyncio.to_thread(self._search_sync,query)
    def _search_sync(self,query):
        token=self._get_token()
        params=urllib.parse.urlencode({"q":query[:100],"limit":50,"sort":"price"})
        url=SEARCH_URL+"?"+params
        headers={"Authorization":"Bearer "+token,"X-EBAY-C-MARKETPLACE-ID":self.marketplace,"Accept-Language":"fr-FR"}
        # Browse API filter syntax explicitly restricts condition to NEW.
        headers["X-EBAY-C-ENDUSERCTX"]="contextualLocation=country%3DFR"
        url += "&filter="+urllib.parse.quote("conditions:{NEW}",safe="{}:,")
        data=self._request(url,headers)
        out=[]
        for row in data.get("itemSummaries",[]):
            condition=row.get("condition")
            if not condition or condition.strip().lower() not in {"new","brand new","new with tags"}:
                continue
            price=row.get("price") or {}
            try: value=float(price.get("value"))
            except (TypeError,ValueError): continue
            if value<=0: continue
            ship=None
            for option in row.get("shippingOptions") or []:
                cost=option.get("shippingCost") or {}
                try: ship=float(cost.get("value")); break
                except (TypeError,ValueError): continue
            seller=(row.get("seller") or {}).get("username")
            url=row.get("itemWebUrl")
            itemid=row.get("itemId")
            out.append(ShoppingCandidate(title=row.get("title",""),price=value,currency=price.get("currency","EUR"),seller=seller,product_url=url,source="ebay_browse",observed_at=datetime.now(timezone.utc),product_id=itemid,shipping_cost=ship,condition=condition,in_stock=True))
        return out
