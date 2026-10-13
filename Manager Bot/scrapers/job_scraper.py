import aiohttp
import logging
from typing import List, Dict, Any
from .utils import strip_html

logger = logging.getLogger("CTRLX.Scrapers.Job")

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
