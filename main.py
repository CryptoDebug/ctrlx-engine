import asyncio
import atexit
import logging
import os
import sys
import psutil
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

PID_FILE = "ctrlx.pid"

def acquire_pid_lock():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                content = f.read().strip()
            if content:
                old_pid = int(content)
                if psutil.pid_exists(old_pid):
                    try:
                        proc = psutil.Process(old_pid)
                        if "python" in proc.name().lower():
                            logger.critical(f"Process already running with PID {old_pid}.")
                            sys.exit(1)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            logger.warning(f"Failed to inspect existing PID file: {e}")

    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        atexit.register(release_pid_lock)
    except Exception as e:
        logger.error(f"Failed to write PID file: {e}")

def release_pid_lock():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                content = f.read().strip()
            if content and int(content) == os.getpid():
                os.remove(PID_FILE)
    except Exception:
        pass

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
    acquire_pid_lock()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
    finally:
        release_pid_lock()
