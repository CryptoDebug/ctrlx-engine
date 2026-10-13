import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import re
import logging
from services.gemini_service import analyze_architecture_or_code, strip_html

logger = logging.getLogger("CTRLX.ReviewCog")

class ReviewCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Analyser l'architecture",
            callback=self.context_review
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def extract_target_details(self, text: str) -> tuple[str, str]:
        match = re.search(r"github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", text)
        if not match:
            return text, ""

        owner, repo = match.group(1), match.group(2).rstrip(".git")
        headers = {"User-Agent": "CTRLX-Review/1.0"}
        info_summary = ""
        readme_sample = ""

        try:
            async with aiohttp.ClientSession() as session:
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        info_summary = (
                            f"Repo: {data.get('full_name')} | Langage: {data.get('language')} | "
                            f"Étoiles: {data.get('stargazers_count')} | Forks: {data.get('forks_count')} | "
                            f"Description: {data.get('description', '')}"
                        )

                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
                async with session.get(raw_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp_raw:
                    if resp_raw.status == 200:
                        readme_text = await resp_raw.text()
                        readme_sample = strip_html(readme_text)[:1200]
        except Exception as e:
            logger.debug(f"Failed to fetch repo context: {e}")

        combined_context = f"{info_summary}\n\nExtrait du README :\n{readme_sample}".strip()
        return f"Dépôt GitHub : https://github.com/{owner}/{repo}", combined_context

    @app_commands.command(name="review", description="Audit technique, architectural et bonnes pratiques d'un projet ou extrait de code.")
    @app_commands.describe(
        cible="Lien de repo GitHub, stack technique ou extrait de code",
        focus="Axe prioritaire de l'audit"
    )
    @app_commands.choices(focus=[
        app_commands.Choice(name="Architecture globale & Structure", value="Architecture globale & Structure"),
        app_commands.Choice(name="Sécurité, Résilience & Auth", value="Sécurité, Résilience & Auth"),
        app_commands.Choice(name="Performance & Scalabilité", value="Performance & Scalabilité"),
        app_commands.Choice(name="Bonnes pratiques & Clean Code", value="Bonnes pratiques & Clean Code")
    ])
    async def review_cmd(self, interaction: discord.Interaction, cible: str, focus: str = "Architecture globale & Structure"):
        await interaction.response.defer(thinking=True)

        target_text, context_info = await self.extract_target_details(cible)
        review_result = await analyze_architecture_or_code(target_text, context_info=context_info, focus=focus)

        await interaction.followup.send(review_result)

    async def context_review(self, interaction: discord.Interaction, message: discord.Message):
        if not message.content.strip():
            await interaction.response.send_message("Le message sélectionné ne contient aucun texte à analyser.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        target_text, context_info = await self.extract_target_details(message.content)
        author_info = f"Auteur du message original : {message.author.display_name} dans #{message.channel.name if hasattr(message.channel, 'name') else 'salon'}"
        if context_info:
            context_info = f"{author_info}\n{context_info}"
        else:
            context_info = author_info

        review_result = await analyze_architecture_or_code(target_text, context_info=context_info, focus="Architecture globale & Structure")
        await interaction.followup.send(review_result)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReviewCog(bot))
