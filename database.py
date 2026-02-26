"""
База данных SQLite для Telegram Stars Bot
"""
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    plan_key    TEXT,
                    stars_paid  INTEGER DEFAULT 0,
                    invites_req INTEGER DEFAULT 0,
                    wish        TEXT,
                    completed   INTEGER DEFAULT 0,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id  INTEGER NOT NULL,
                    invited_id  INTEGER NOT NULL UNIQUE,
                    created_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (inviter_id) REFERENCES users(user_id)
                );
            """)

    # ── Пользователи ──────────────────────────────────────────────────────
    def add_user(self, user_id: int, usernastr, referrer_id: int = None)::
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username),

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
            )

    def set_user_plan(self, user_id: int, plan_key: str, stars: int, invites: int):
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE users
                   SET plan_key=?, stars_paid=?, invites_req=?
                   WHERE user_id=?""",
                (plan_key, stars, invites, user_id),
            )

    def get_user_plan(self, user_id: int) -> str:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT plan_key FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            return row["plan_key"] if row else "plan_100"

    def save_wish(self, user_id: int, wish: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET wish=? WHERE user_id=?",
                (wish, user_id),
            )

    def get_wish(self, user_id: int) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT wish FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            return row["wish"] if row else None

    def mark_completed(self, user_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE users SET completed=1 WHERE user_id=?", (user_id,)
            )

    # ── Рефералы ──────────────────────────────────────────────────────────
    def register_referral(self, inviter_id: int, invited_id: int):
        """Регистрируем, кто пришёл по чьей ссылке."""
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
                    (inviter_id, invited_id),
                )
            except sqlite3.IntegrityError:
                pass  # уже зарегистрирован

    def count_referrals(self, user_id: int) -> int:
        """Сколько человек перешло по ссылке user_id."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM referrals WHERE inviter_id=?",
                (user_id,),
            ).fetchone()
            return row["cnt"] if row else 0

    # ── Статистика (для админа) ────────────────────────────────────────────
    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            paid = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE stars_paid > 0"
            ).fetchone()["c"]
            wishes = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE wish IS NOT NULL"
            ).fetchone()["c"]
            completed = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE completed=1"
            ).fetchone()["c"]
            stars_row = conn.execute(
                "SELECT SUM(stars_paid) AS s FROM users"
            ).fetchone()
            total_stars = stars_row["s"] or 0
        return {
            "total_users": total,
            "paid_users": paid,
            "wishes": wishes,
            "completed": completed,
            "total_stars": total_stars,
        }
