import discord
from discord.ext import tasks
import logging
from config import (
    CHANNEL_TECH_RADAR, RADAR_INTERVAL_MINUTES
)
import time
from services.feeds_service import fetch_radar_items
from services.gemini_service import format_tech_radar_news
from database import is_item_posted, mark_item_posted, get_last_posted_timestamp

logger = logging.getLogger("CTRLX.RadarPoster")

def setup_radar_task(bot: discord.Client):
    @tasks.loop(minutes=RADAR_INTERVAL_MINUTES)
    async def radar_loop():
        try:
            last_ts = get_last_posted_timestamp("radar")
            if time.time() - last_ts < (RADAR_INTERVAL_MINUTES * 60) - 30:
                return

            channel = bot.get_channel(CHANNEL_TECH_RADAR)
            if not channel:
                logger.warning(f"Radar channel ({CHANNEL_TECH_RADAR}) not found.")
                return

            items = await fetch_radar_items()
            for it in items:
                url = it.get("link", "")
                if not is_item_posted("radar", url):
                    title = it.get("title", "")
                    summary = it.get("summary", "")
                    domain = it.get("domain", "Tech")

                    formatted_text = await format_tech_radar_news(title, summary, url, domain)
                    await channel.send(formatted_text)

                    mark_item_posted("radar", url, title, url)
                    logger.info(f"Radar post: {title[:50]}")
                    break
        except Exception as e:
            logger.error(f"Error in radar_loop: {e}")

    @radar_loop.before_loop
    async def before_radar():
        await bot.wait_until_ready()

    radar_loop.start()
    return radar_loop
