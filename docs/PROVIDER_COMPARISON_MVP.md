# Source-data provider comparison — Price Hunter Radar MVP

Research checked **22 November 2026**. Provider prices, access conditions and coverage may change; re-check before purchasing or production launch.

## Decision

**Primary provider: DataForSEO Google Shopping Products API (paid, guarded). Second provider now connected: Pricewatcha public search API (read-only, anonymous quota, no key), guarded to 3 calls/day.** This is the best technical proof-of-concept for broad European retailer discovery because it returns structured shopping listings (title, price, currency, seller, rating and result identifiers), supports location/language, and is billed by task. DataForSEO documents task-post/task-get async flow and task depth; normal priority avoids the additional high-priority cost. Its published Standard/normal price is to be checked in the provider dashboard before use; an external comparison currently reports $0.001 per SERP/product result, but that price is not guaranteed and should not be treated as a committed quote.

**Important limitations:** Google Shopping is an aggregator/search layer, not a merchant-authoritative stock or checkout source. Its listings do not reliably prove condition (new), shipping, final checkout total, seller legitimacy, or stock. Candidates from this provider must remain REVIEW until these facts are independently verified. The API may also miss stores/products and results are location-dependent.

## Options compared

| Provider/source | Cost/access | Coverage/useful data | Decision |
|---|---|---|---|
| **DataForSEO Google Shopping** | Pay per task/result; reported low per-SERP pricing; no monthly subscription assumption | Broad product/merchant discovery; location/language; seller, price, ratings; async task API | **MVP candidate** — cost control and breadth; verify live price and account minimum |
| **Pricewatcha API** | Public catalog reads and tracking with anonymous quotas; key raises quotas; limits are published and may change | Product search, current price/history, product URL tracking, alerts/webhooks; catalog coverage dependent on its database | **Fallback / trial** — convenient no-key evaluation, but provider coverage/terms and data provenance need due diligence |
| **Keepa** | Paid token subscription; third-party guide reports starter €49/month; official token-based model | Excellent Amazon-only price history, offers, seller, deals and rank | **Not first** — excellent Amazon intelligence but subscription cost and Amazon-only scope |
| **Awin product feeds / affiliate network feeds** | Affiliate approval/account and advertiser-specific availability; feeds are subject to affiliate terms | Product catalog and merchant-provided price/availability, often deep and trackable links | **Phase 2** — more permissioned and useful for monetization; limited to approved advertisers and feed coverage |
| **Retailer official APIs / partner feeds** | Often free or negotiated, but access/coverage varies; requires partnership or program approval | Most authoritative for that retailer; inventory and price data may be richer | **Best per retailer when available**, but not scalable as the sole discovery source |
| **Google Shopping direct/other SERP APIs** | Provider-specific; price and quotas vary | Search-layer cross-retailer discovery | Alternative provider only if cost/coverage benchmarks better |
| **Scraping infrastructure (Zyte, Bright Data, Oxylabs, ScraperAPI)** | Paid, usage-dependent; complexity and site-specific compliance | Can cover sites not served by feeds/APIs, but failures and maintenance increase | **Not for initial MVP** — avoid anti-bot bypass, CAPTCHA, authenticated pages, or terms-violating collection |

## Why DataForSEO wins for this MVP

1. Pay-as-you-go is a better fit than a fixed monthly subscription while the project has no revenue.
2. Google Shopping can discover multiple merchants from one query.
3. France/French location and language can be configured.
4. It supports a standard asynchronous task flow.
5. The adapter can be isolated behind a provider interface, so Keepa, Awin feeds, or retailer APIs can be added without rewriting the bot.
6. We can test a handful of search terms and establish the real cost before committing to volume.

## Safe cost controls before enabling it

- Provider remains disabled until credentials are configured.
- Keep scanner off by default.
- Start with 3–5 manually selected queries, no more than once daily.
- Depth 40, normal priority only.
- Do not schedule full category crawls.
- Log provider cost/task count and stop if budget guard is exceeded.
- Set a hard monthly budget in the provider account if supported.
- Cache each query and suppress repeat tasks within 24 hours.
- Never auto-publish a result solely because it is cheap or has a crossed-out old price.

## DataForSEO fields and mapping

DataForSEO Google Shopping Products returns product listing fields such as `title`, `price`, `currency`, `seller`, `url`/shopping URL, `product_id`, rating, reviews, and sometimes `old_price`. It does **not** reliably supply the facts Price Hunter's quality gate needs: new condition, confirmed stock, exact seller identity, shipping cost, or checkout total. Do not fill those fields with assumptions.

## Suggested phase order

1. **Provider smoke test:** create DataForSEO account, inspect live cost for France, normal priority, depth 40, one query.
2. **Adapter:** `bot/providers/dataforseo_shopping.py` (included in this branch); tests mock the provider payload and do not use credentials.
3. **Review queue:** persist candidates; mark incomplete data REVIEW. No public posting.
4. **Merchant verification:** add an approved merchant-specific API/feed or human verification of exact listing, condition, stock and shipping.
5. **Scoring:** price competitiveness score only after reliable comparison references; never equate old price with true historical price.
6. **Controlled Telegram integration:** preview and manual approval first; auto-publish later only for candidates that pass quality, freshness, policy, duplicate and budget checks.

## Sources

- DataForSEO Google Shopping Products task-post documentation: https://docs.dataforseo.com/v3/merchant/google/products/task_post/
- DataForSEO Google Shopping overview: https://docs.dataforseo.com/v3/merchant/overview/
- DataForSEO Google Shopping product data and sellers: https://docs.dataforseo.com/v3/merchant/google/products/task_get/advanced/
- DataForSEO pricing: https://dataforseo.com/pricing/merchant/google-shopping-api
- Pricewatcha API docs: https://pricewatcha.com/en/developers
- Keepa API documentation: https://keepa.com/api-docs/
- Keepa plans/tokens: https://keepa.com/api-docs/plans-tokens.html
- Awin product feed documentation: https://help.awin.com/apidocs/retail-advertiser-productapidocumentation
- Amazon Associates policies: https://partenaires.amazon.fr/help/operating/policies?language=fr_FR

Amazon note: Amazon PA-API v5 has been retired in 2026; Creators API is the successor and is subject to eligibility and affiliate program requirements. Do not build a new PA-API v5 integration.


## Pricewatcha integration status

Pricewatcha's public `GET /api/v1/search?q=…&limit=…` endpoint is connected as a second provider in `bot/providers/pricewatcha.py`. Anonymous access is documented, but public read/search is subject to quotas and potential restrictions if used abusively. Price Hunter's local cap is intentionally set to 3 searches/day and can be disabled with `PRICEWATCHA_ENABLED=false`. The connector filters demo preview/inactive/malformed results; it does not infer condition. Candidates flow through the existing explicit-new condition gate and Review Queue. Search data is third-party price intelligence, not an independent direct merchant feed.
