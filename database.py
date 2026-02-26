""""""  

import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id       INTEGER PRIMARY KEY,
                    username      TEXT,
                    plan_key      TEXT,
                    stars_paid    INTEGER DEFAULT 0,
                    invites_req   INTEGER DEFAULT 0,
                    wish          TEXT,
                    completed     INTEGER DEFAULT 0,
                    created_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id    INTEGER NOT NULL,
                    invited_id    INTEGER NOT NULL UNIQUE,
                    created_at    TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (inviter_id) REFERENCES users(user_id)
                );
                """
            )

    # ---- Пользователи ----

    def add_user(self, user_id: int, username: str, referrer_id: int = None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username),
            )

            # Обработка реферала
            if referrer_id:
                conn.execute(
                    """INSERT INTO referrals (inviter_id, invited_id) 
                    VALUES (?, ?)""",
                    (referrer_id, user_id),
                )
                # Добавляем билет рефереру
                conn.execute(
                    """UPDATE users SET invites_req = invites_req + 1 
                    WHERE user_id=?""",
                    (referrer_id,),
                )

    def add_tickets(self, user_id: int, count: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET invites_req = invites_req + ? WHERE user_id=?",
                (count, user_id),
            )

    def add_wish(self, user_id: int, wish: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET wish=? WHERE user_id=?",
                (wish, user_id),
            )

    def get_user_tickets(self, user_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT invites_req FROM users WHERE user_id=?",
                (user_id,),
            ).fetchone()
            return row["invites_req"] if row else 0

    def get_user_invites(self, user_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM referrals WHERE inviter_id=?",
                (user_id,),
            ).fetchone()
            return row["cnt"] if row else 0

    def get_user_info(self, user_id: int):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if row:
                return dict(row)
            return None

    # ---- Админ ----

    def get_stats(self):
        with self._get_conn() as conn:
            total_users = conn.execute(
                "SELECT COUNT(*) as cnt FROM users"
            ).fetchone()["cnt"]
            total_tickets = conn.execute(
                "SELECT SUM(invites_req) as sm FROM users"
            ).fetchone()["sm"] or 0
            total_wishes = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE wish IS NOT NULL"
            ).fetchone()["cnt"]

            return {
                "total_users": total_users,
                "total_tickets": total_tickets,
                "total_wishes": total_wishes,
            }

    def draw_winner(self):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, invites_req FROM users WHERE invites_req > 0"
            ).fetchall()

            if not rows:
                return None

            import random

            tickets = []
            for row in rows:
                user_id = row["user_id"]
                count = row["invites_req"]
                tickets.extend([user_id] * count)

            return random.choice(tickets) if tickets else None
