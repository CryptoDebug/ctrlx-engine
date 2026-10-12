import discord
from discord.ext import tasks
import logging
from config import CHANNEL_STAFF_OWNERS, BREAKING_CHECK_MINUTES
from services.feeds_service import fetch_radar_items, check_for_breaking_event
from cogs.interactive_views import BreakingNewsApprovalView
from database import is_item_posted, mark_item_posted

logger = logging.getLogger("CTRLX.BreakingChecker")

def setup_breaking_task(bot: discord.Client):
    @tasks.loop(minutes=BREAKING_CHECK_MINUTES)
    async def breaking_loop():
        try:
            staff_channel = bot.get_channel(CHANNEL_STAFF_OWNERS)
            if not staff_channel:
                return

            items = await fetch_radar_items()
            for it in items:
                title = it.get("title", "")
                summary = it.get("summary", "")
                url = it.get("link", "")

                if check_for_breaking_event(title, summary):
                    if not is_item_posted("breaking_pending", url):
                        embed = discord.Embed(
                            title="🚨 [ALERTE DÉTECTÉE] Breaking News Tech Majeure",
                            description=(
                                f"**Titre :** {title}\n\n"
                                f"**Résumé :** {summary[:400]}...\n\n"
                                f"**Lien :** {url}\n\n"
                                f"👉 *Choisissez le salon de destination et le type de mention ci-dessous, puis validez ou rejetez.*"
                            ),
                            color=discord.Color.red()
                        )
                        embed.set_footer(text="CTRLX Detection Engine")

                        view = BreakingNewsApprovalView(title, summary, url)
                        await staff_channel.send(embed=embed, view=view)

                        mark_item_posted("breaking_pending", url, title, url)
                        logger.info(f"Breaking news sent to staff: {title}")
        except Exception as e:
            logger.error(f"Error in breaking_loop: {e}")

    @breaking_loop.before_loop
    async def before_breaking():
        await bot.wait_until_ready()

    breaking_loop.start()
    return breaking_loop
