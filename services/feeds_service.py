import aiohttp
import feedparser
import asyncio
import datetime
import logging
import html
import re
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

def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

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

async def fetch_security_advisories() -> List[Dict[str, Any]]:
    items = []
    headers = {"User-Agent": "CTRLX-Community-Bot/1.0"}
    ecosystems = [("npm", "Node.js"), ("pip", "Python"), ("go", "Go"), ("rust", "Rust")]

    try:
        async with aiohttp.ClientSession() as session:
            for eco_code, eco_label in ecosystems:
                url = f"https://api.github.com/advisories?ecosystem={eco_code}&per_page=3"
                try:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for adv in data:
                                sev = str(adv.get("severity", "")).lower()
                                if sev in ["critical", "high"]:
                                    ghsa_id = adv.get("ghsa_id", "")
                                    summary = strip_html(adv.get("summary", ""))
                                    desc = strip_html(adv.get("description", ""))
                                    html_url = adv.get("html_url", "")
                                    if summary and html_url:
                                        items.append({
                                            "title": f"[{eco_label}] {ghsa_id} : {summary}",
                                            "link": html_url,
                                            "summary": f"Sévérité {sev.upper()}. {desc[:280]}",
                                            "domain": "Cyber",
                                            "source": f"GitHub Advisory ({eco_label})"
                                        })
                except Exception as e:
                    logger.debug(f"Error fetching advisories for {eco_code}: {e}")

            try:
                nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=docker&resultsPerPage=2"
                async with session.get(nvd_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        nvd_data = await resp.json()
                        for v in nvd_data.get("vulnerabilities", []):
                            cve = v.get("cve", {})
                            cve_id = cve.get("id", "")
                            descs = cve.get("descriptions", [])
                            desc_text = descs[0].get("value", "") if descs else ""
                            if cve_id and desc_text:
                                items.append({
                                    "title": f"[Docker] {cve_id} : Vulnérabilité signalée",
                                    "link": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                                    "summary": strip_html(desc_text)[:280],
                                    "domain": "Cyber",
                                    "source": "NVD (Docker)"
                                })
            except Exception as e:
                logger.debug(f"Error fetching NVD docker CVEs: {e}")
    except Exception as e:
        logger.error(f"Error in fetch_security_advisories: {e}")

    return items

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

async def fetch_radar_items() -> List[Dict[str, Any]]:
    items = []
    advisories = await fetch_security_advisories()
    items.extend(advisories)
    trending = await fetch_github_trending_repos()
    items.extend(trending)
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

                        raw_desc = strip_html(j.get("description", ""))

                        jobs.append({
                            "title": strip_html(j.get("title", "")),
                            "company": strip_html(j.get("company_name", "")),
                            "url": j.get("url", ""),
                            "description": raw_desc[:600],
                            "location": strip_html(j.get("candidate_required_location", "Remote")),
                            "job_type": job_type,
                            "salary": strip_html(j.get("salary", "Selon profil"))
                        })
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
    return jobs

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
