# Price Hunter Radar

Telegram control bot and price-alert project. The scanner remains disabled until a permitted product-data source is connected.

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
- `/scan`: remains unavailable until a permitted product-data source is connected.

## GitHub Actions

The CI workflow checks Python syntax and runs the quality-control unit tests on pushes, pull requests and manual dispatch. It does **not** host the Telegram bot continuously and does **not** scan product prices.

A scheduled scanner still requires a permitted product-data source, persistence between runs and integration of the quality gate into the collector-to-alert pipeline. Never publish an offer as orderable without verifying seller, condition, stock, shipping and final checkout price.
