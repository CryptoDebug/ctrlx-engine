import aiohttp
import feedparser
import asyncio
import logging
from typing import List, Dict, Any
from .utils import strip_html

logger = logging.getLogger("CTRLX.Scrapers.Feed")

RADAR_SOURCES = [
    {"domain": "Cyber", "url": "https://www.bleepingcomputer.com/feed/", "name": "BleepingComputer"},
    {"domain": "Cyber", "url": "https://feeds.feedburner.com/TheHackersNews", "name": "The Hacker News"},
    {"domain": "Dev", "url": "https://dev.to/feed", "name": "Dev.to"},
    {"domain": "Tech", "url": "https://news.ycombinator.com/rss", "name": "Hacker News"},
    {"domain": "Hardware", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "name": "Ars Technica"},
    {"domain": "Web3", "url": "https://decrypt.co/feed", "name": "Decrypt"}
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

async def fetch_general_radar_items() -> List[Dict[str, Any]]:
    items = []
    for src in RADAR_SOURCES:
        entries = await fetch_rss_entries(src["url"])
        for entry in entries[:5]:
            title = strip_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "").strip()
            summary = strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:300],
                    "domain": src["domain"],
                    "source": src["name"]
                })
    return items
