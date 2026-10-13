import aiohttp
import asyncio
import datetime
import logging
from typing import List, Dict, Any
from .utils import strip_html
from .feed_scraper import fetch_rss_entries

logger = logging.getLogger("CTRLX.Scrapers.GitHub")

TECH_RELEASES_SOURCES = [
    {"name": "Bun", "url": "https://github.com/oven-sh/bun/releases.atom"},
    {"name": "Rust", "url": "https://github.com/rust-lang/rust/releases.atom"},
    {"name": "uv (Astral)", "url": "https://github.com/astral-sh/uv/releases.atom"},
    {"name": "Next.js", "url": "https://github.com/vercel/next.js/releases.atom"},
    {"name": "Go", "url": "https://github.com/golang/go/releases.atom"},
    {"name": "Zig", "url": "https://github.com/ziglang/zig/releases.atom"}
]

async def fetch_github_trending_repos() -> List[Dict[str, Any]]:
    items = []
    headers = {"User-Agent": "CTRLX-Community-Bot/1.0"}
    cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=21)).strftime("%Y-%m-%d")
    url = f"https://api.github.com/search/repositories?q=created:>{cutoff_date}+stars:>80&sort=stars&order=desc&per_page=6"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for repo in data.get("items", []):
                        full_name = repo.get("full_name", "")
                        html_url = repo.get("html_url", "")
                        desc = strip_html(repo.get("description", "") or "Projet open-source émergent")
                        lang = repo.get("language") or "Outil"
                        stars = repo.get("stargazers_count", 0)

                        if full_name and html_url:
                            items.append({
                                "title": f"📦 [Open Source] {full_name} ({lang}) : {desc[:100]}",
                                "link": html_url,
                                "summary": f"⭐ {stars:,} étoiles. Langage : {lang}. Description : {desc[:280]}",
                                "domain": "Dev",
                                "source": "GitHub Trending"
                            })
    except Exception as e:
        logger.debug(f"Error fetching trending repos: {e}")

    return items

async def fetch_tech_releases() -> List[Dict[str, Any]]:
    releases = []
    for tech in TECH_RELEASES_SOURCES:
        entries = await fetch_rss_entries(tech["url"])
        for entry in entries[:2]:
            title = strip_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "").strip()
            content = getattr(entry, "summary", "") or getattr(entry, "content", "")
            if isinstance(content, list) and content:
                content = content[0].get("value", "")
            if title and link:
                releases.append({
                    "tech_name": tech["name"],
                    "title": title,
                    "link": link,
                    "details": strip_html(str(content))[:600]
                })
    return releases
