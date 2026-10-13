import discord
from discord.ext import tasks
import logging
from config import (
    CHANNEL_TUTORIALS_COURSES, TAG_TUTO_DEV, TAG_TUTO_TOOLS,
    TUTORIALS_CHECK_HOURS
)
from services.feeds_service import fetch_tech_releases
from services.gemini_service import generate_tutorial_for_tech
from database import is_item_posted, mark_item_posted

logger = logging.getLogger("CTRLX.TutorialsPoster")

async def find_existing_thread(forum_channel: discord.ForumChannel, tech_name: str):
    target = tech_name.lower().strip()

    for th in forum_channel.threads:
        if target in th.name.lower():
            return th

    try:
        async for th in forum_channel.archived_threads(limit=100):
            if target in th.name.lower():
                return th
    except Exception as e:
        logger.debug(f"Archived threads lookup error: {e}")

    return None

def setup_tutorials_task(bot: discord.Client):
    @tasks.loop(hours=TUTORIALS_CHECK_HOURS)
    async def tutorials_loop():
        try:
            forum_channel = bot.get_channel(CHANNEL_TUTORIALS_COURSES)
            if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
                logger.warning(f"Tutorials forum ({CHANNEL_TUTORIALS_COURSES}) not found.")
                return

            releases = await fetch_tech_releases()
            for rel in releases:
                url = rel.get("link", "")
                tech_name = rel.get("tech_name", "")
                if not is_item_posted("tutorial", url):
                    details = rel.get("details", "")
                    tuto = await generate_tutorial_for_tech(tech_name, details, url)
                    if not tuto:
                        continue

                    thread_name = tuto.get("name", f"🚀 Découverte : {tech_name}")[:95]
                    content = tuto.get("content", "")

                    existing_thread = await find_existing_thread(forum_channel, tech_name)

                    if existing_thread:
                        if existing_thread.archived:
                            try:
                                await existing_thread.edit(archived=False)
                            except Exception:
                                pass

                        update_msg = f"📢 **Nouvelle version / Mise à jour : {tech_name}**\n\n{content}"
                        await existing_thread.send(update_msg)
                        logger.info(f"Appended update to existing thread '{existing_thread.name}'")
                    else:
                        tag_ids = [int(TAG_TUTO_DEV), int(TAG_TUTO_TOOLS)]
                        applied_tags = [t for t in forum_channel.available_tags if t.id in tag_ids]

                        await forum_channel.create_thread(
                            name=thread_name,
                            content=content,
                            applied_tags=applied_tags
                        )
                        logger.info(f"Created new tutorial thread: {thread_name}")

                    mark_item_posted("tutorial", url, thread_name, url)
                    break
        except Exception as e:
            logger.error(f"Error in tutorials_loop: {e}")

    @tutorials_loop.before_loop
    async def before_tutorials():
        await bot.wait_until_ready()

    tutorials_loop.start()
    return tutorials_loop
