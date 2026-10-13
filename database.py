import sqlite3
import hashlib
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                item_hash TEXT UNIQUE NOT NULL,
                title TEXT,
                url TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_hash ON posted_items(item_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON posted_items(category)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS breaking_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_url TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_metrics (
                metric_key TEXT PRIMARY KEY,
                metric_value INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                topic_summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_category ON topic_history(category)")
        conn.commit()

def compute_hash(val: str) -> str:
    return hashlib.sha256(val.strip().lower().encode('utf-8')).hexdigest()

def is_item_posted(category: str, identifier: str) -> bool:
    h = compute_hash(identifier)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM posted_items WHERE item_hash = ?", (h,))
        return cursor.fetchone() is not None

def mark_item_posted(category: str, identifier: str, title: str = "", url: str = ""):
    h = compute_hash(identifier)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO posted_items (category, item_hash, title, url)
            VALUES (?, ?, ?, ?)
        """, (category, h, title, url))
        
        cursor.execute("""
            INSERT INTO bot_metrics (metric_key, metric_value)
            VALUES (?, 1)
            ON CONFLICT(metric_key) DO UPDATE SET metric_value = metric_value + 1
        """, (f"posts_{category}",))
        conn.commit()

def record_topic(category: str, topic_summary: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO topic_history (category, topic_summary)
            VALUES (?, ?)
        """, (category, topic_summary.strip()))
        conn.commit()

def get_recent_topics(category: str, limit: int = 15) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT topic_summary FROM topic_history
            WHERE category = ?
            ORDER BY id DESC LIMIT ?
        """, (category, limit))
        return [row['topic_summary'] for row in cursor.fetchall()]

def increment_metric(metric: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bot_metrics (metric_key, metric_value)
            VALUES (?, 1)
            ON CONFLICT(metric_key) DO UPDATE SET metric_value = metric_value + 1
        """, (metric,))
        conn.commit()

def get_metric(metric: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT metric_value FROM bot_metrics WHERE metric_key = ?", (metric,))
        row = cursor.fetchone()
        return row['metric_value'] if row else 0

def get_all_metrics() -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT metric_key, metric_value FROM bot_metrics")
        return {r['metric_key']: r['metric_value'] for r in cursor.fetchall()}
