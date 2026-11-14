# Price Hunter Radar — roadmap

## Included
- Telegram bot restricted to the configured chat ID
- /start, /help, /status, /watchlist, /add, /remove, /pause, /resume and /scan
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
Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the hosting provider's secret settings. Optionally set DATABASE_PATH. Do not commit a real .env file.
