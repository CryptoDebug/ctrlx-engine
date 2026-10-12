import aiohttp
import feedparser
import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger("CTRLX.Feeds")

RADAR_SOURCES = [
    {"domain": "Cyber", "url": "https://www.bleepingcomputer.com/feed/", "name": "BleepingComputer"},
    {"domain": "Cyber", "url": "https://feeds.feedburner.com/TheHackersNews", "name": "The Hacker News"},
    {"domain": "Dev", "url": "https://dev.to/feed", "name": "Dev.to"},
    {"domain": "Tech", "url": "https://news.ycombinator.com/rss", "name": "Hacker News"},
    {"domain": "Hardware", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "name": "Ars Technica"},
    {"domain": "Web3", "url": "https://decrypt.co/feed", "name": "Decrypt"}
]

TECH_RELEASES_SOURCES = [
    {"name": "Bun", "url": "https://github.com/oven-sh/bun/releases.atom"},
    {"name": "Rust", "url": "https://github.com/rust-lang/rust/releases.atom"},
    {"name": "uv (Astral)", "url": "https://github.com/astral-sh/uv/releases.atom"},
    {"name": "Next.js", "url": "https://github.com/vercel/next.js/releases.atom"},
    {"name": "Go", "url": "https://github.com/golang/go/releases.atom"},
    {"name": "Zig", "url": "https://github.com/ziglang/zig/releases.atom"}
]

async def fetch_rss_entries(feed_url: str, timeout: int = 15) -> List[Dict[str, Any]]:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CTRLXBot/1.0"}
            async with session.get(feed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    feed = await asyncio.to_thread(feedparser.parse, text)
                    return feed.entries
    except Exception as e:
        logger.debug(f"Feed error {feed_url}: {e}")
    return []

async def fetch_radar_items() -> List[Dict[str, Any]]:
    items = []
    for src in RADAR_SOURCES:
        entries = await fetch_rss_entries(src["url"])
        for entry in entries[:5]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:300],
                    "domain": src["domain"],
                    "source": src["name"]
                })
    return items

async def fetch_remote_jobs() -> List[Dict[str, Any]]:
    jobs = []
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=15"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "CTRLX-Community-Bot/1.0"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for j in data.get("jobs", []):
                        job_type = "CDI / CDD"
                        t_lower = j.get("job_type", "").lower()
                        if "freelance" in t_lower or "contract" in t_lower:
                            job_type = "Mission Freelance"
                        elif "intern" in t_lower:
                            job_type = "Stage"

                        jobs.append({
                            "title": j.get("title", ""),
                            "company": j.get("company_name", ""),
                            "url": j.get("url", ""),
                            "description": j.get("description", "")[:600],
                            "location": j.get("candidate_required_location", "Remote"),
                            "job_type": job_type,
                            "salary": j.get("salary", "Selon profil")
                        })
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
    return jobs

async def fetch_tech_releases() -> List[Dict[str, Any]]:
    releases = []
    for tech in TECH_RELEASES_SOURCES:
        entries = await fetch_rss_entries(tech["url"])
        for entry in entries[:2]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            content = getattr(entry, "summary", "") or getattr(entry, "content", "")
            if isinstance(content, list) and content:
                content = content[0].get("value", "")
            if title and link:
                releases.append({
                    "tech_name": tech["name"],
                    "title": title,
                    "link": link,
                    "details": str(content)[:600]
                })
    return releases

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
