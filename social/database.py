import sqlite3
import time
from config import SOCIAL_DB_PATH

def get_connection():
    conn = sqlite3.connect(SOCIAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_social_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                item_id TEXT NOT NULL,
                author TEXT DEFAULT '',
                title TEXT DEFAULT '',
                url TEXT DEFAULT '',
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, item_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_seen_plat_item ON seen_items(platform, item_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                target_url TEXT DEFAULT '',
                content TEXT NOT NULL,
                status TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_created ON social_actions(platform, created_at)")
        conn.commit()

def is_item_seen(platform: str, item_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_items WHERE platform = ? AND item_id = ?",
            (platform, str(item_id))
        )
        return cursor.fetchone() is not None

def mark_item_seen(platform: str, item_id: str, author: str = "", title: str = "", url: str = ""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO seen_items (platform, item_id, author, title, url)
            VALUES (?, ?, ?, ?, ?)
        """, (platform, str(item_id), author[:100], title[:250], url[:250]))
        conn.commit()

def record_action(platform: str, action_type: str, target_id: str, content: str, target_url: str = "", status: str = "success"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO social_actions (platform, action_type, target_id, target_url, content, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (platform, action_type, str(target_id), target_url, content, status))
        conn.commit()

def get_action_count_today(platform: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM social_actions
            WHERE platform = ? AND created_at >= date('now', 'start of day')
        """, (platform,))
        row = cursor.fetchone()
        return int(row["count"]) if row else 0

def get_recent_actions(limit: int = 10) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT platform, action_type, target_id, content, status, created_at
            FROM social_actions
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
