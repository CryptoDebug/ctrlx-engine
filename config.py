import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

CHANNEL_OFFRES_EMPLOI = int(os.getenv("CHANNEL_OFFRES_EMPLOI", "0"))
CHANNEL_CONSEILS_CARRIERE = int(os.getenv("CHANNEL_CONSEILS_CARRIERE", "0"))
CHANNEL_ETUDES_FORMATIONS = int(os.getenv("CHANNEL_ETUDES_FORMATIONS", "0"))
CHANNEL_TECH_RADAR = int(os.getenv("CHANNEL_TECH_RADAR", "0"))
CHANNEL_TUTORIALS_COURSES = int(os.getenv("CHANNEL_TUTORIALS_COURSES", "0"))
CHANNEL_OFF_TOPIC = int(os.getenv("CHANNEL_OFF_TOPIC", "0"))
CHANNEL_TECH_TALK = int(os.getenv("CHANNEL_TECH_TALK", "0"))
CHANNEL_STAFF_OWNERS = int(os.getenv("CHANNEL_STAFF_OWNERS", "0"))

ROLE_VEILLE_TECH = int(os.getenv("ROLE_VEILLE_TECH", "0"))
ROLE_OPPORTUNITES = int(os.getenv("ROLE_OPPORTUNITES", "0"))

TAG_STAGE = os.getenv("TAG_STAGE", "")
TAG_ALTERNANCE = os.getenv("TAG_ALTERNANCE", "")
TAG_CDI_CDD = os.getenv("TAG_CDI_CDD", "")
TAG_FREELANCE = os.getenv("TAG_FREELANCE", "")

TAG_TUTO_TOOLS = os.getenv("TAG_TUTO_TOOLS", "")
TAG_TUTO_OSINT = os.getenv("TAG_TUTO_OSINT", "")
TAG_TUTO_CYBER = os.getenv("TAG_TUTO_CYBER", "")
TAG_TUTO_DEV = os.getenv("TAG_TUTO_DEV", "")
TAG_TUTO_IA = os.getenv("TAG_TUTO_IA", "")

RADAR_INTERVAL_MINUTES = int(os.getenv("RADAR_INTERVAL_MINUTES", "35"))
JOB_INTERVAL_HOURS = int(os.getenv("JOB_INTERVAL_HOURS", "4"))
CAREER_INTERVAL_HOURS = int(os.getenv("CAREER_INTERVAL_HOURS", "72"))
FORMATION_INTERVAL_HOURS = int(os.getenv("FORMATION_INTERVAL_HOURS", "96"))
TUTORIALS_CHECK_HOURS = int(os.getenv("TUTORIALS_CHECK_HOURS", "12"))
BREAKING_CHECK_MINUTES = int(os.getenv("BREAKING_CHECK_MINUTES", "15"))

DB_PATH = os.path.join(os.path.dirname(__file__), "ctrlx_data.sqlite")
