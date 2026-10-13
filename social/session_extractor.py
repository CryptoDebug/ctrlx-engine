import os
import sqlite3
import tempfile
import shutil
import glob
import logging

logger = logging.getLogger("CTRLX.Social.SessionExtractor")

def get_firefox_profile_dir() -> str | None:
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None

    profiles_pattern = os.path.join(appdata, "Mozilla", "Firefox", "Profiles", "*")
    profiles = glob.glob(profiles_pattern)
    if not profiles:
        return None

    profiles_with_cookies = []
    for p in profiles:
        cookie_file = os.path.join(p, "cookies.sqlite")
        if os.path.exists(cookie_file):
            profiles_with_cookies.append((os.path.getmtime(cookie_file), p))

    if not profiles_with_cookies:
        return None

    profiles_with_cookies.sort(key=lambda x: x[0], reverse=True)
    return profiles_with_cookies[0][1]

def extract_cookies() -> dict:
    profile_dir = get_firefox_profile_dir()
    if not profile_dir:
        logger.warning("No active Firefox profile found.")
        return {}

    cookie_file = os.path.join(profile_dir, "cookies.sqlite")
    temp_sqlite = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite").name

    try:
        shutil.copy2(cookie_file, temp_sqlite)
    except Exception as e:
        logger.error(f"Error copying cookies.sqlite: {e}")
        return {}

    cookies = {}
    try:
        conn = sqlite3.connect(temp_sqlite)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT host, name, value FROM moz_cookies
            WHERE (host LIKE '%reddit.com%' AND name IN ('token_v2', 'reddit_session'))
               OR (host LIKE '%x.com%' AND name IN ('auth_token', 'ct0', 'twid'))
               OR (host LIKE '%twitter.com%' AND name IN ('auth_token', 'ct0', 'twid'))
        """)
        for host, name, value in cursor.fetchall():
            cookies[name] = value
    except Exception as e:
        logger.error(f"Error reading cookies: {e}")
    finally:
        conn.close()
        if os.path.exists(temp_sqlite):
            try:
                os.remove(temp_sqlite)
            except OSError:
                pass

    return cookies

def sync_sessions_to_env():
    cookies = extract_cookies()
    if not cookies:
        return False

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    keys_to_update = {
        "REDDIT_TOKEN_V2": cookies.get("token_v2", ""),
        "REDDIT_SESSION": cookies.get("reddit_session", ""),
        "TWITTER_AUTH_TOKEN": cookies.get("auth_token", ""),
        "TWITTER_CT0": cookies.get("ct0", ""),
        "TWITTER_USER_ID": cookies.get("twid", "").replace("u%3D", "")
    }

    updated_keys = set()
    new_lines = []

    for line in existing_lines:
        line_stripped = line.strip()
        matched = False
        for k, v in keys_to_update.items():
            if line_stripped.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                updated_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in keys_to_update.items():
        if k not in updated_keys and v:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logger.info("Successfully extracted and synchronized Firefox active sessions!")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = sync_sessions_to_env()
    print("Sync status:", success)
