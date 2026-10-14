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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facebook_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL UNIQUE,
                group_name TEXT NOT NULL,
                group_url TEXT NOT NULL,
                status TEXT DEFAULT 'discovered',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_posted_at TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_groups_posted ON facebook_groups(last_posted_at)")
        conn.commit()

def is_item_seen(platform: str, item_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_items WHERE platform = ? AND item_id = ?",
            (platform, str(item_id))
        )
        return cursor.fetchone() is not None

def has_acted_on(platform: str, target_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM social_actions WHERE platform = ? AND target_id = ?",
            (platform, str(target_id))
        )
        return cursor.fetchone() is not None

def is_content_already_used(content: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM social_actions WHERE content = ? AND status = 'success'",
            (content.strip(),)
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
            WHERE platform = ? AND status = 'success' AND created_at >= date('now', 'start of day')
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

def add_facebook_group(group_id: str, group_name: str, group_url: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO facebook_groups (group_id, group_name, group_url)
            VALUES (?, ?, ?)
        """, (str(group_id), group_name[:200], group_url[:300]))
        conn.commit()
        return cursor.rowcount > 0

def get_available_facebook_groups(limit: int = 10) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT group_id, group_name, group_url, last_posted_at
            FROM facebook_groups
            WHERE last_posted_at IS NULL OR last_posted_at <= datetime('now', '-2 days')
            ORDER BY last_posted_at ASC NULLS FIRST
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def mark_facebook_group_posted(group_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE facebook_groups
            SET last_posted_at = CURRENT_TIMESTAMP
            WHERE group_id = ?
        """, (str(group_id),))
        conn.commit()

def count_facebook_groups() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM facebook_groups")
        row = cursor.fetchone()
        return int(row["c"]) if row else 0

