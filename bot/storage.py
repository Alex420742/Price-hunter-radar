import sqlite3
from pathlib import Path

class Storage:
    def __init__(self, database_path: str):
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS watchlist (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('paused', 'false')")
    def _connect(self):
        return sqlite3.connect(self.database_path)
    def is_paused(self) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()
        return bool(row and row[0] == 'true')
    def set_paused(self, paused: bool) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('paused', ?)", ('true' if paused else 'false',))
    def add_watch(self, query: str) -> bool:
        with self._connect() as db:
            return db.execute("INSERT OR IGNORE INTO watchlist(query) VALUES(?)", (query,)).rowcount > 0
    def remove_watch(self, query: str) -> bool:
        with self._connect() as db:
            return db.execute("DELETE FROM watchlist WHERE query=?", (query,)).rowcount > 0
    def list_watchlist(self) -> list[str]:
        with self._connect() as db:
            rows = db.execute("SELECT query FROM watchlist ORDER BY query COLLATE NOCASE").fetchall()
        return [row[0] for row in rows]
