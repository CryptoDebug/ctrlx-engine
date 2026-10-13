import aiohttp
import logging
from typing import List, Dict, Any
from .utils import strip_html

logger = logging.getLogger("CTRLX.Scrapers.Security")

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
