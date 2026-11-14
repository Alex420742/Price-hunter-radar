# Price Hunter Radar — roadmap

## Included
- Telegram bot restricted to the configured private control chat ID
- Separate destination channel configuration
- /start, /help, /status, /watchlist, /add, /remove, /pause, /resume, /testchannel and /scan
- SQLite watchlist and pause state
- Docker deployment baseline
- Environment template; no credentials committed

## Not yet implemented
- Amazon product API integration
- European marketplace discovery
- Price anomaly scoring and reference-price validation
- Seller, condition, stock and checkout verification
- Scheduled scans and automatic deal alerts

The scan command deliberately remains unavailable until a permitted product-data source and detection engine are integrated. Do not use unauthorized scraping or bypass anti-bot controls. Never call an offer orderable without checking seller, condition, stock and checkout.

## Runtime secrets
Set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and TELEGRAM_CHANNEL_ID in the hosting provider's secret settings. TELEGRAM_CHAT_ID is your private numeric control-chat ID; TELEGRAM_CHANNEL_ID is the destination channel ID. The destination bot must be an administrator with permission to publish. Do not commit a real .env file.
