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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                domains TEXT DEFAULT '',
                speciality TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                github_url TEXT DEFAULT '',
                portfolio_url TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                feedback_karma INTEGER DEFAULT 0,
                ships_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giver_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message_id INTEGER DEFAULT 0,
                channel_id INTEGER DEFAULT 0,
                reason TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_giver ON feedback_transactions(giver_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fb_receiver ON feedback_transactions(receiver_id)")
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

def get_last_posted_timestamp(category: str) -> float:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT unixepoch(posted_at) as ts FROM posted_items
            WHERE category = ?
            ORDER BY id DESC LIMIT 1
        """, (category,))
        row = cursor.fetchone()
        return float(row['ts']) if row and row['ts'] else 0.0

def get_user_profile(user_id: int) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            "user_id": user_id,
            "domains": "",
            "speciality": "",
            "skills": "",
            "github_url": "",
            "portfolio_url": "",
            "bio": "",
            "feedback_karma": 0,
            "ships_count": 0
        }

def upsert_user_profile(user_id: int, domains: str, speciality: str, skills: str, github_url: str, portfolio_url: str, bio: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_profiles (user_id, domains, speciality, skills, github_url, portfolio_url, bio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                domains = excluded.domains,
                speciality = excluded.speciality,
                skills = excluded.skills,
                github_url = excluded.github_url,
                portfolio_url = excluded.portfolio_url,
                bio = excluded.bio,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, domains.strip(), speciality.strip(), skills.strip(), github_url.strip(), portfolio_url.strip(), bio.strip()))
        conn.commit()

def record_feedback_transaction(giver_id: int, receiver_id: int, message_id: int = 0, channel_id: int = 0, reason: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback_transactions (giver_id, receiver_id, message_id, channel_id, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (giver_id, receiver_id, message_id, channel_id, reason.strip()))

        cursor.execute("""
            INSERT INTO user_profiles (user_id, feedback_karma)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET feedback_karma = feedback_karma + 1
        """, (receiver_id,))

        cursor.execute("SELECT feedback_karma FROM user_profiles WHERE user_id = ?", (receiver_id,))
        row = cursor.fetchone()
        new_karma = row['feedback_karma'] if row else 1
        conn.commit()
        return new_karma

def get_last_feedback_given_time(giver_id: int) -> float:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT unixepoch(created_at) as ts FROM feedback_transactions
            WHERE giver_id = ?
            ORDER BY id DESC LIMIT 1
        """, (giver_id,))
        row = cursor.fetchone()
        return float(row['ts']) if row and row['ts'] else 0.0

def increment_user_ships(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_profiles (user_id, ships_count)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET ships_count = ships_count + 1
        """, (user_id,))
        cursor.execute("SELECT ships_count FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        new_ships = row['ships_count'] if row else 1
        conn.commit()
        return new_ships

def get_feedback_leaderboard(limit: int = 10) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, feedback_karma, ships_count, speciality, domains
            FROM user_profiles
            WHERE feedback_karma > 0
            ORDER BY feedback_karma DESC, ships_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def get_ships_leaderboard(limit: int = 10) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, ships_count, feedback_karma, speciality, domains
            FROM user_profiles
            WHERE ships_count > 0
            ORDER BY ships_count DESC, feedback_karma DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
