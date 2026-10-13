import asyncio
import logging
import sys
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID, CHANNEL_SHIP_LOG
from database import init_db
from tasks.radar_poster import setup_radar_task
from tasks.job_poster import setup_job_task
from tasks.career_poster import setup_career_tasks
from tasks.tutorials_poster import setup_tutorials_task
from tasks.breaking_checker import setup_breaking_task

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CTRLX.Core")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == CHANNEL_SHIP_LOG:
        content_lower = message.content.lower()
        has_build = any(k in content_lower for k in ["build", "avancé", "avance", "worked on"])
        has_tools = any(k in content_lower for k in ["stack", "outil", "tools"])

        if not (has_build and has_tools):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Tu dois respecter le format obligatoire pour poster dans ce salon. Consulte le message épinglé pour copier le template !",
                    delete_after=15
                )
            except Exception as e:
                logger.error(f"Error moderating ship-log message: {e}")
            return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    logger.info(f"Connected: {bot.user} (ID: {bot.user.id})")

    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        logger.error(f"Command sync error: {e}")

    try:
        setup_radar_task(bot)
        setup_job_task(bot)
        setup_career_tasks(bot)
        setup_tutorials_task(bot)
        setup_breaking_task(bot)
        logger.info("All background tasks initialized.")
    except Exception as e:
        logger.error(f"Error starting tasks: {e}")

async def main():
    init_db()
    await bot.load_extension("cogs.admin_cog")

    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN missing.")
        return

    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
