# Price Hunter Radar

Telegram control bot and price-alert project. The current scanner is intentionally disabled until a permitted product-data source and validated anomaly detector are integrated.

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
- `/scan`: currently reports that scanning is unavailable until a permitted data source is connected.

## Current limitation

Telegram delivery is being prepared, but automatic deal detection is not implemented yet. No Amazon prices, discounts or pricing errors are currently scanned or verified.
