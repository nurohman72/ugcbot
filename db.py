import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    chat_id INTEGER PRIMARY KEY,
                    step TEXT,
                    product_photos TEXT DEFAULT '[]',
                    ai_analyses TEXT DEFAULT '[]',
                    user_descriptions TEXT DEFAULT '[]',
                    model_type TEXT,
                    ai_gender TEXT,
                    ai_age_group TEXT,
                    model_photo_path TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    prompt TEXT,
                    photo_path TEXT,
                    status TEXT,
                    created_at TIMESTAMP
                )
            """)

    def get_session(self, chat_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM sessions WHERE chat_id = ?", (chat_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_session(self, chat_id):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (chat_id, created_at, updated_at) "
                "VALUES (?, ?, ?)",
                (chat_id, now, now),
            )

    def update_session(self, chat_id, **kwargs):
        now = datetime.now().isoformat()
        kwargs["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [chat_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE sessions SET {set_clause} WHERE chat_id = ?", values
            )

    def log_generation(self, chat_id, prompt, photo_path, status):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO generation_log (chat_id, prompt, photo_path, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (chat_id, prompt, photo_path, status, now),
            )
