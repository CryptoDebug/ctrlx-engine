import os
from dotenv import load_dotenv

env_path_social = os.path.join(os.path.dirname(__file__), ".env")
env_path_parent = os.path.join(os.path.dirname(__file__), "..", ".env")

if os.path.exists(env_path_social):
    load_dotenv(env_path_social)
elif os.path.exists(env_path_parent):
    load_dotenv(env_path_parent)
else:
    load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "").strip()
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "").strip()
REDDIT_TOKEN_V2 = os.getenv("REDDIT_TOKEN_V2", "").strip()
REDDIT_SESSION = os.getenv("REDDIT_SESSION", "").strip()
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0").strip()

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "").strip()
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "").strip()
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "").strip()
TWITTER_AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
TWITTER_CT0 = os.getenv("TWITTER_CT0", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DISCORD_INVITE_URL = os.getenv("DISCORD_INVITE_URL", "https://discord.gg/ctrlx").strip()

MONITORED_SUBREDDITS = [
    s.strip() for s in os.getenv(
        "MONITORED_SUBREDDITS",
        "developpeurs,france_tech,SideProject,webdev,Python"
    ).split(",") if s.strip()
]

TWITTER_SEARCH_QUERIES = [
    q.strip() for q in os.getenv(
        "TWITTER_SEARCH_QUERIES",
        "side project dev,build in public fr,projet tech dev,besoin feedback dev"
    ).split(",") if q.strip()
]

MAX_REDDIT_ACTIONS_PER_DAY = int(os.getenv("MAX_REDDIT_ACTIONS_PER_DAY", "6"))
MAX_TWITTER_ACTIONS_PER_DAY = int(os.getenv("MAX_TWITTER_ACTIONS_PER_DAY", "10"))
COOLDOWN_BETWEEN_ACTIONS_SEC = int(os.getenv("COOLDOWN_BETWEEN_ACTIONS_SEC", "120"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")

SOCIAL_DB_PATH = os.path.join(os.path.dirname(__file__), "social_data.sqlite")
