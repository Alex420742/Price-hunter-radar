# Price Hunter Radar — Phase 1 Implementation Plan

**Purpose:** turn the existing Telegram control bot into a safe, measurable deal-detection MVP without rebuilding the project.

## Verified baseline (repository audit)
- Python Telegram bot with private-chat authorization.
- Commands: start/help/status/watchlist/add/remove/pause/resume/testchannel/scan.
- SQLite currently stores watchlist and pause state.
- Offer quality gate exists in `bot/quality_control.py`.
- Unit tests cover quality gate.
- Docker baseline and GitHub Actions CI exist.
- Scanner is deliberately disabled; no collector or live deal pipeline is connected.
- No price history, product catalog, merchant catalog, commercial deal score, deduplication, or scheduled scanning yet.

## Product principles
1. New products only (used/refurbished excluded).
2. No published offer without a verifiable source, exact product identity, seller, new condition, stock, total price/shipping and fresh observation.
3. A low price is a lead, never proof of a pricing error.
4. Use official APIs, affiliate feeds, permitted product feeds and other sources whose terms allow the use. No anti-bot/CAPTCHA bypass.
5. Separate trust/quality scoring from commercial deal scoring.
6. Keep Telegram as the first distribution channel; don't build a large web dashboard before validated audience traction.
7. Preserve secrets outside Git.

## Target MVP architecture
- **Source adapters:** provider-specific modules, one stable interface.
- **Normalizer:** product identifiers and variants (EAN/GTIN, brand, model, MPN, ASIN where appropriate); do not merge distinct configurations.
- **Persistence:** SQLite initially, with schema designed to migrate to PostgreSQL when scale justifies it.
- **Price observations:** timestamp, country, merchant, seller, currency, shipping, condition, stock, source, URL and product identity.
- **Detection:** cross-retailer gap, historic price drop (only where adequate history exists), threshold/watchlist, and price-error candidate.
- **Quality gate:** existing gate extended conservatively; REJECT/REVIEW/APPROVED statuses.
- **Deal score:** separate 0–100 score based on discount vs robust reference, historical evidence, merchant trust, data confidence, product demand and offer quality.
- **Deduplication:** canonical product/offer key and time-based suppression.
- **Publisher:** format, affiliate URL only when legitimately available, publish Telegram, store message ID and status.
- **Post-publication check:** revalidate offer periodically; mark expired internally and avoid claiming stock if stale.
- **Scheduler:** interval by source and rate limits; scanner paused by default until configuration/consent checks complete.
- **Observability:** logs, metrics, errors, last successful source run, source quota, and publication failures.

## Recommended build order
### P0 — Make the baseline safe and testable
- Confirm CI green.
- Review command authorization, configuration validation and database behavior.
- Improve tests for malformed inputs, stale data, missing source, price references and time-zone handling.
- Add explicit scanner readiness checks; keep scanning off by default.

### P1 — Provider proof of concept (one data source)
- Pick one permitted provider/API/feed and document coverage, price fields, quotas, licensing, and cost.
- Add adapter and integration tests with mocked responses.
- Demonstrate a real product search and price observation without publishing.
- Decide if this source can cover the first category (electronics/tech) adequately.

### P2 — Data model and history
Tables: products, merchants, offers, price_observations, deals, published_alerts, watchlist, source_runs, settings.
- Use UTC timestamps.
- Store currency as ISO 4217.
- Store both item price and shipping; derive landed total.
- Index product identity, merchant, observation time and active offers.
- Use migration scripts; never silently drop user data.

### P3 — Detection and scoring
- Cross-market comparison only after exact variant matching and shipping normalization.
- Historical score only when sample size and time coverage are adequate; otherwise lower confidence.
- Robust references (median, minimum, percentiles) rather than a single arbitrary list price.
- Separate scores: quality/trust and deal value.
- Extreme anomalies always go to manual review until false-positive rate is demonstrated.

### P4 — Telegram publication
- Channel test remains separate from live publishing.
- Preview command for candidate deal.
- Manual approve/reject command for review queue.
- Auto-publish only when quality passes, deal threshold passes, source is permitted and fresh, and duplicate suppression passes.
- Include price, reference and basis, merchant/seller, shipping, stock observation time, product link, affiliate disclosure where applicable.
- Store Telegram message ID, timestamp and deal ID.

### P5 — Growth and monetization
- Affiliate programs only after their current terms and Telegram/social traffic rules are checked.
- Track clicks using compliant tracking methods.
- Launch free channel first; premium only after users demonstrate demand for speed, watchlists or customization.
- Content strategy: daily/weekly best deals, anomaly explainers, short videos and transparent deal reviews.

## Initial score proposal (calibrate using real data; do not treat as validated)
Quality gate: 0–100, critical failures reject, incomplete/stale information review.
Deal score weights:
- 30% discount against robust market reference
- 20% price history evidence
- 15% merchant trust
- 15% product value/demand
- 10% data confidence
- 10% total offer quality (shipping, stock, returns/warranty)
Thresholds:
- <50: ignore
- 50–64: watch/review
- 65–79: standard deal candidate
- 80–89: hot deal
- 90+: anomaly/jackpot candidate, mandatory review
These weights and thresholds must be tuned; no score guarantees a deal is good.

## Source evaluation checklist
For each candidate source:
- Legal/terms permission and relevant API/feed licensing
- EU country coverage and merchant coverage
- Exact variant identifiers
- Item price, currency, shipping and final total
- Seller identity and condition
- Stock/availability reliability
- Update cadence, latency and quota
- Historic data availability
- Affiliate support and disclosure rules
- Cost at expected volume
- Reliability and failure handling

## First 30-day acceptance criteria
1. Scanner remains disabled until source permissions/configuration are verified.
2. One adapter successfully records product observations in tests and a controlled live proof.
3. No duplicate observations or alerts caused by repeated identical scans.
4. Quality and deal scores have separate unit tests.
5. Candidate deals can be previewed and reviewed in private chat.
6. Only approved candidates can publish; rejected/review items never auto-publish.
7. Telegram posts include accurate fields and affiliate disclosure when applicable.
8. CI runs syntax, tests and lint/type checks added incrementally.
9. Secrets are never committed.
10. A daily report shows source health, candidates, approvals, rejections, posts, clicks and failures.

## Non-goals for MVP
- 3,000-site crawling.
- A full mobile app.
- Paid premium subscriptions.
- Complex AI agents on every scan.
- Multi-country deployment before one source and one country/category are reliable.
- Any claim of confirmed price error without human/merchant confirmation.

## Next decision gate
Before implementing a live collector, select and validate a permitted data source. Compare the available provider/API options against the checklist and test coverage. The project can then implement an adapter without locking its architecture to one vendor.
