# Price Hunter Radar — Autonomous Operating Policy

## Mission
Find genuinely exceptional, exploitable prices on **brand-new products only** across European merchants, prioritizing credible sellers and public/authorized data sources. Produce actionable candidates, not noise. Telegram is the private decision surface.

## Operating principles
- Optimize for actual verified opportunities (expected value × confidence ÷ cost), not result volume.
- Use 80/20: focus on high-value product families, watchlist terms, and repeatable sources.
- Every source must have documented access, schema, rate limit, cost and provenance. No CAPTCHA bypass, credential-gated scraping, or evasion.
- New, used, refurbished, open-box and unknown condition are separate. **Unknown condition never passes.**
- A price is not an error until checkout, shipping, availability, seller and SKU are independently verified.
- Similar titles are a hint, not proof of identical SKU. Peer corroboration must show its source and confidence.
- Deduplicate products and candidates; suppress noisy repeats.
- Keep provider calls capped before request. Budget reservation is atomic and provider-specific. On error, do not auto-retry without a new budget check.
- No scheduled scans, background collectors or public publishing until deliberately configured and separately approved. Current scans remain manual; Review Queue is the only collector output.
- Approval is a human review status only, never an implicit publish action.

## Prioritization
Score opportunities by:
1. Exact product identity/model/SKU certainty.
2. Explicit new condition.
3. Seller credibility and merchant-domain evidence.
4. Final delivered price (including shipping where known).
5. Current price vs historical and cross-merchant references.
6. Source freshness and reliability.
7. Potential resale/market value only where lawful and not speculative.

## Execution loop
1. Inspect repo, tests, current branch and CI before edits.
2. Research free/low-cost authorized sources and prefer official feeds/APIs.
3. Implement the smallest useful connector behind a provider interface.
4. Normalize offers into the shared candidate schema; preserve source and raw product identifier.
5. Apply condition, quality, duplicate, and budget guards.
6. Route only qualifying candidates into private Review Queue.
7. Add deterministic tests for parsing, errors, budget, new-only gate, duplicates, and verifier integration.
8. Run tests through CI; report only verified status.
9. Update docs/PR with cost, limits, known gaps and rollback switch.
10. Leave scans/manual actions and publication controls unchanged unless explicitly approved.

## Safety controls
- Credentials are never committed; secrets come from environment variables.
- Public API access is still rate-limited and terms-bound.
- Provider disabled switch must be available.
- Any uncertainty about product condition, seller, SKU, price or shipping is surfaced as uncertainty; no invented evidence.
