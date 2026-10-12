import discord
from discord.ext import tasks
import logging
from config import (
    CHANNEL_CONSEILS_CARRIERE, CHANNEL_ETUDES_FORMATIONS,
    CAREER_INTERVAL_HOURS, FORMATION_INTERVAL_HOURS
)
from services.gemini_service import generate_career_tip, generate_formation_guide
from database import mark_item_posted, increment_metric

logger = logging.getLogger("CTRLX.CareerPoster")

def setup_career_tasks(bot: discord.Client):
    @tasks.loop(hours=CAREER_INTERVAL_HOURS)
    async def career_loop():
        try:
            channel = bot.get_channel(CHANNEL_CONSEILS_CARRIERE)
            if not channel:
                logger.warning(f"Career channel ({CHANNEL_CONSEILS_CARRIERE}) not found.")
                return

            tip = await generate_career_tip()
            if tip:
                await channel.send(tip)
                mark_item_posted("career", tip[:50], "Conseil Carrière CTRLX", "")
                increment_metric("posts_career")
                logger.info("Career tip posted.")
        except Exception as e:
            logger.error(f"Error in career_loop: {e}")

    @tasks.loop(hours=FORMATION_INTERVAL_HOURS)
    async def formation_loop():
        try:
            channel = bot.get_channel(CHANNEL_ETUDES_FORMATIONS)
            if not channel:
                logger.warning(f"Formation channel ({CHANNEL_ETUDES_FORMATIONS}) not found.")
                return

            guide = await generate_formation_guide()
            if guide:
                await channel.send(guide)
                mark_item_posted("formation", guide[:50], "Guide Études & Certifications", "")
                increment_metric("posts_formation")
                logger.info("Formation guide posted.")
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
