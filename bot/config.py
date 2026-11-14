from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    database_path: str
    scanner_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")
        return cls(token, chat_id, os.getenv("DATABASE_PATH", "data/price_hunter.db"), os.getenv("SCANNER_ENABLED", "false").lower() == "true")
