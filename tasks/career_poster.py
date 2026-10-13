import discord
from discord.ext import tasks
import logging
from config import (
    CHANNEL_CONSEILS_CARRIERE, CHANNEL_ETUDES_FORMATIONS,
    CAREER_INTERVAL_HOURS, FORMATION_INTERVAL_HOURS
)
import time
from services.gemini_service import generate_career_tip, generate_formation_guide
from database import mark_item_posted, increment_metric, record_topic, get_recent_topics, get_last_posted_timestamp

logger = logging.getLogger("CTRLX.CareerPoster")

def setup_career_tasks(bot: discord.Client):
    @tasks.loop(hours=CAREER_INTERVAL_HOURS)
    async def career_loop():
        try:
            last_ts = get_last_posted_timestamp("career")
            if time.time() - last_ts < (CAREER_INTERVAL_HOURS * 3600) - 60:
                return

            channel = bot.get_channel(CHANNEL_CONSEILS_CARRIERE)
            if not channel:
                logger.warning(f"Career channel ({CHANNEL_CONSEILS_CARRIERE}) not found.")
                return

            recent_topics = get_recent_topics("career", limit=20)
            tip = await generate_career_tip(exclude_topics=recent_topics)
            if tip:
                await channel.send(tip)
                
                title_line = tip.split("\n")[0].replace("#", "").strip()
                record_topic("career", title_line)
                mark_item_posted("career", tip[:50], title_line, "")
                increment_metric("posts_career")
                logger.info(f"Career tip posted: {title_line}")
        except Exception as e:
            logger.error(f"Error in career_loop: {e}")

    @tasks.loop(hours=FORMATION_INTERVAL_HOURS)
    async def formation_loop():
        try:
            last_ts = get_last_posted_timestamp("formation")
            if time.time() - last_ts < (FORMATION_INTERVAL_HOURS * 3600) - 60:
                return

            channel = bot.get_channel(CHANNEL_ETUDES_FORMATIONS)
            if not channel:
                logger.warning(f"Formation channel ({CHANNEL_ETUDES_FORMATIONS}) not found.")
                return

            recent_topics = get_recent_topics("formation", limit=20)
            guide = await generate_formation_guide(exclude_topics=recent_topics)
            if guide:
                await channel.send(guide)
                
                title_line = guide.split("\n")[0].replace("#", "").strip()
                record_topic("formation", title_line)
                mark_item_posted("formation", guide[:50], title_line, "")
                increment_metric("posts_formation")
                logger.info(f"Formation guide posted: {title_line}")
        except Exception as e:
            logger.error(f"Error in formation_loop: {e}")

    @career_loop.before_loop
    async def before_career():
        await bot.wait_until_ready()

    @formation_loop.before_loop
    async def before_formation():
        await bot.wait_until_ready()

    career_loop.start()
    formation_loop.start()
    return career_loop, formation_loop
