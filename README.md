# Price Hunter Radar

Telegram control bot and price-alert project. The collector is connected for manual `/scan` commands only. Scheduled scans remain off; offers are never automatically published.

## Automatic quality control

A first automatic quality gate is available in `bot/quality_control.py`. It evaluates candidate offers before alert publication and returns one of three statuses:

- `APPROVED`: required checks are satisfied.
- `REVIEW`: data is incomplete, stale or needs human verification.
- `REJECTED`: critical information is invalid or the item is not new.

Checks include product identity, positive price, supported currency, seller identity, new condition, confirmed stock, shipping cost, source, observation timestamp and independent reference prices. Extreme price gaps are flagged for manual verification; a very low price is never treated as proof of a confirmed pricing error.

The quality gate is implemented and unit-tested, but it is **not yet connected to a live product collector or Telegram alert pipeline**. Therefore it does not currently scan stores or publish verified deals.

## Telegram setup

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Add the bot as an administrator to the destination channel and allow it to publish messages.
3. Set these environment variables in the hosting provider:
   - `TELEGRAM_BOT_TOKEN`: bot token from BotFather.
   - `TELEGRAM_CHAT_ID`: your personal numeric Telegram chat ID; this is the private control chat allowed to use commands.
   - `TELEGRAM_CHANNEL_ID`: destination channel ID. The current channel is `-1001875596181`.
4. Start the bot and send it `/start` in a private chat.
5. Run `/testchannel` to verify that the bot can publish to the channel.

Never commit a real token or a populated `.env` file.

## Current commands

- `/status`: bot, scanner and channel configuration status.
- `/watchlist`, `/add <product>`, `/remove <product>`: manage tracked product names.
- `/pause`, `/resume`: pause or resume scanning.
- `/testchannel`: send a controlled test post to the destination channel.
- `/scan`: manually invokes DataForSEO with watchlist, query cap and daily API budget; candidates go only to the private review queue.

## GitHub Actions

The CI workflow checks Python syntax and runs the quality-control unit tests on pushes, pull requests and manual dispatch. It does **not** host the Telegram bot continuously and does **not** scan product prices.

A scheduled scanner still requires a permitted product-data source, persistence between runs and integration of the quality gate into the collector-to-alert pipeline. Never publish an offer as orderable without verifying seller, condition, stock, shipping and final checkout price.


## Price Engine (manual-review foundation)

- SQLite price observations with timestamps, source, seller, URL, shipping, condition and stock; unknown values remain NULL.
- 90-day history query and median baseline after at least five prior observations.
- Heuristic anomaly score and discount percentage. This is a lead, not proof of a price error.
- Atomic daily API budget reservation with request-count and estimated USD caps.
- Telegram Review Queue commands: `/review`, `/approve <id>`, `/reject <id>`. Candidates default to pending.
- `/approve` marks a candidate approved for a later step only; it never posts to the channel.

The DataForSEO collector is wired to the watchlist for manual `/scan` only. It enforces a daily request/budget guard, caps queries per scan, deduplicates observations and queue candidates, and rejects any candidate without an explicit new-condition field. Google Shopping results commonly omit condition, so those results are deliberately excluded rather than assumed new. No scheduled scan or auto-publishing is enabled.

## Manual collector controls

Environment variables (optional conservative defaults):
- DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD: provider credentials; missing credentials block the scan before any call.
- PRICEHUNTER_MAX_QUERIES_PER_SCAN: default 3 watchlist queries per manual scan.
- PRICEHUNTER_DAILY_REQUEST_LIMIT: default 5 tasks/day.
- PRICEHUNTER_DAILY_BUDGET_USD: default $1/day estimated ceiling.
- DATAFORSEO_ESTIMATED_TASK_COST_USD: default $0.001/task; adjust to actual plan/charges.

Only explicit provider condition values new, neuf, brand new, or new in box pass the strict new-product gate. Unknown/used items are discarded. Review Queue is private and no handler posts candidates to the public channel.
