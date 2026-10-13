import discord
from discord.ext import tasks
import logging
from config import (
    CHANNEL_OFFRES_EMPLOI, ROLE_OPPORTUNITES,
    TAG_STAGE, TAG_ALTERNANCE, TAG_CDI_CDD, TAG_FREELANCE,
    JOB_INTERVAL_HOURS
)
import time
from services.feeds_service import fetch_remote_jobs
from services.gemini_service import format_job_offer
from database import is_item_posted, mark_item_posted, get_last_posted_timestamp

logger = logging.getLogger("CTRLX.JobPoster")

def setup_job_task(bot: discord.Client):
    @tasks.loop(hours=JOB_INTERVAL_HOURS)
    async def job_loop():
        try:
            last_ts = get_last_posted_timestamp("job")
            if time.time() - last_ts < (JOB_INTERVAL_HOURS * 3600) - 60:
                return

            forum_channel = bot.get_channel(CHANNEL_OFFRES_EMPLOI)
            if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
                logger.warning(f"Job forum channel ({CHANNEL_OFFRES_EMPLOI}) not found.")
                return

            jobs = await fetch_remote_jobs()
            for job in jobs:
                url = job.get("url", "")
                if not is_item_posted("job", url):
                    title = job.get("title", "")
                    company = job.get("company", "")
                    desc = job.get("description", "")
                    j_type = job.get("job_type", "CDI / CDD")
                    loc = job.get("location", "Remote")

                    formatted = await format_job_offer(title, company, desc, url, j_type, loc)
                    thread_title = formatted.get("thread_title", f"{company} - {title}")[:95]
                    content = formatted.get("content", "")

                    target_tag_id = int(TAG_CDI_CDD)
                    if j_type == "Stage":
                        target_tag_id = int(TAG_STAGE)
                    elif j_type == "Alternance":
                        target_tag_id = int(TAG_ALTERNANCE)
                    elif j_type == "Mission Freelance":
                        target_tag_id = int(TAG_FREELANCE)

                    applied_tags = [t for t in forum_channel.available_tags if t.id == target_tag_id]

                    thread_result = await forum_channel.create_thread(
                        name=thread_title,
                        content=content,
                        applied_tags=applied_tags
                    )
                    
                    if ROLE_OPPORTUNITES:
                        try:
                            await thread_result.thread.send(f"<@&{ROLE_OPPORTUNITES}> Nouvelle offre disponible !")
                        except Exception:
                            pass

                    mark_item_posted("job", url, thread_title, url)
                    logger.info(f"Job posted: {thread_title}")
                    break
        except Exception as e:
            logger.error(f"Error in job_loop: {e}")

    @job_loop.before_loop
    async def before_job():
        await bot.wait_until_ready()

    job_loop.start()
    return job_loop
