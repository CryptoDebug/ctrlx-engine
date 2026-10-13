import logging
from typing import List, Dict, Any
from scrapers import (
    strip_html,
    RADAR_SOURCES,
    TECH_RELEASES_SOURCES,
    fetch_rss_entries,
    fetch_general_radar_items,
    fetch_security_advisories,
    fetch_github_trending_repos,
    fetch_tech_releases,
    fetch_remote_jobs
)

logger = logging.getLogger("CTRLX.FeedsService")

async def fetch_radar_items() -> List[Dict[str, Any]]:
    items = []
    advisories = await fetch_security_advisories()
    items.extend(advisories)
    trending = await fetch_github_trending_repos()
    items.extend(trending)
    general_items = await fetch_general_radar_items()
    items.extend(general_items)
    return items

def check_for_breaking_event(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    critical_triggers = [
        "zero-day exploited in the wild",
        "0-day in the wild",
        "cvss 10.0",
        "cvss 10 ",
        "critical remote code execution",
        "massive global outage",
        "gpt-5 released",
        "claude 4 released",
        "gemini 4 released",
        "breach affects hundreds of millions"
    ]
    return any(trig in text for trig in critical_triggers)
