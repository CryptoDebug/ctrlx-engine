import discord
from discord import app_commands
from discord.ext import commands
import os
import psutil
import time
from datetime import timedelta
import logging
from config import (
    CHANNEL_STAFF_OWNERS, CHANNEL_OFFRES_EMPLOI, CHANNEL_TECH_RADAR,
    CHANNEL_CONSEILS_CARRIERE, CHANNEL_ETUDES_FORMATIONS,
    TAG_CDI_CDD, DB_PATH
)
from database import get_all_metrics, mark_item_posted
from services.social_service import generate_social_pack
from services.feeds_service import fetch_remote_jobs, fetch_radar_items
from services.gemini_service import (
    format_job_offer, format_tech_radar_news,
    generate_career_tip, generate_formation_guide
)
from cogs.interactive_views import SocialStudioView, BreakingNewsApprovalView

logger = logging.getLogger("CTRLX.AdminCog")

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="status", description="Affiche l'état de santé, la RAM et les statistiques du bot CTRLX.")
    async def status_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        uptime = timedelta(seconds=int(time.time() - self.start_time))

        db_size_kb = 0
        if os.path.exists(DB_PATH):
            db_size_kb = os.path.getsize(DB_PATH) / 1024

        metrics = get_all_metrics()
        posts_radar = metrics.get("posts_radar", 0)
        posts_jobs = metrics.get("posts_job", 0)
        posts_career = metrics.get("posts_career", 0)
        posts_formation = metrics.get("posts_formation", 0)
        posts_tutorials = metrics.get("posts_tutorial", 0)

        embed = discord.Embed(
            title="⚡ Statut Système & Métriques CTRLX Bot",
            color=discord.Color.blue()
        )
        embed.add_field(name="🧠 Mémoire RAM", value=f"`{mem_mb:.1f} MB`", inline=True)
        embed.add_field(name="⚙️ CPU Serveur", value=f"`{cpu_percent}%`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"`{uptime}`", inline=True)
        embed.add_field(name="💾 Base SQLite", value=f"`{db_size_kb:.1f} KB`", inline=True)
        embed.add_field(name="📡 Latence Discord", value=f"`{self.bot.latency * 1000:.1f} ms`", inline=True)
        embed.add_field(name="🤖 Version", value="`CTRLX Engine v2.0`", inline=True)

        embed.add_field(
            name="📊 Publications Cumulées",
            value=(
                f"• **Tech Radar :** `{posts_radar}` posts\n"
                f"• **Offres Emploi :** `{posts_jobs}` fiches\n"
                f"• **Conseils Carrière :** `{posts_career}` guides\n"
                f"• **Formations :** `{posts_formation}` fiches\n"
                f"• **Tutoriels Majeurs :** `{posts_tutorials}` cours"
            ),
            inline=False
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="social-generate", description="Génère un kit de posts prêts à copier pour LinkedIn, X et Reddit.")
    @app_commands.describe(sujet="Thème du post à générer")
    async def social_generate_cmd(self, interaction: discord.Interaction, sujet: str = "la veille tech et l'entraide entre développeurs sur CTRLX"):
        await interaction.response.defer(ephemeral=False)

        social_pack = await generate_social_pack(sujet)

        embed = discord.Embed(
            title=f"📢 CTRLX Social Studio • {sujet[:60]}",
            description="Voici les 3 variantes optimisées pour chaque plateforme. Cliquez sur les boutons pour copier le texte brut.",
            color=discord.Color.gold()
        )
        embed.add_field(name="💼 Aperçu LinkedIn", value=f"{social_pack.get('linkedin', '')[:350]}...", inline=False)
        embed.add_field(name="🐦 Aperçu X (Twitter)", value=f"{social_pack.get('twitter', '')[:250]}", inline=False)
        embed.add_field(name="👽 Aperçu Reddit", value=f"{social_pack.get('reddit', '')[:350]}...", inline=False)

        view = SocialStudioView(social_pack)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="job-force", description="Force la recherche et publication immédiate d'une offre d'emploi.")
    async def job_force_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        forum = self.bot.get_channel(CHANNEL_OFFRES_EMPLOI)
        if not forum or not isinstance(forum, discord.ForumChannel):
            await interaction.followup.send("Salon forum offres d'emploi introuvable.", ephemeral=True)
            return

        jobs = await fetch_remote_jobs()
        if not jobs:
            await interaction.followup.send("Aucune offre disponible actuellement.", ephemeral=True)
            return

        job = jobs[0]
        formatted = await format_job_offer(job['title'], job['company'], job['description'], job['url'], job['job_type'], job['location'])
        thread_title = formatted.get("thread_title", f"{job['company']} - {job['title']}")[:95]
        content = formatted.get("content", "")

        tags = [t for t in forum.available_tags if t.id == int(TAG_CDI_CDD)]
        thread_res = await forum.create_thread(name=thread_title, content=content, applied_tags=tags)

        mark_item_posted("job", job['url'], thread_title, job['url'])
        await interaction.followup.send(f"✅ Offre publiée dans {thread_res.thread.mention} !", ephemeral=True)

    @app_commands.command(name="radar-force", description="Force la publication immédiate d'un flash info dans #tech-radar.")
    async def radar_force_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = self.bot.get_channel(CHANNEL_TECH_RADAR)
        if not channel:
            await interaction.followup.send("Salon tech-radar introuvable.", ephemeral=True)
            return

        items = await fetch_radar_items()
        if not items:
            await interaction.followup.send("Aucune actualité disponible.", ephemeral=True)
            return

        it = items[0]
        formatted = await format_tech_radar_news(it['title'], it['summary'], it['link'], it['domain'])
        await channel.send(formatted)
        mark_item_posted("radar", it['link'], it['title'], it['link'])
        await interaction.followup.send(f"✅ Flash info publié dans {channel.mention} !", ephemeral=True)

    @app_commands.command(name="career-force", description="Force la publication d'un conseil ou guide de formation.")
    @app_commands.choices(rubrique=[
        app_commands.Choice(name="Conseil Carrière (dans #conseils-carrière)", value="career"),
        app_commands.Choice(name="Études & Formations (dans #études-et-formations)", value="formation")
    ])
    async def career_force_cmd(self, interaction: discord.Interaction, rubrique: str):
        await interaction.response.defer(ephemeral=True)
        from database import get_recent_topics, record_topic
        if rubrique == "career":
            ch = self.bot.get_channel(CHANNEL_CONSEILS_CARRIERE)
            recent = get_recent_topics("career", limit=20)
            text = await generate_career_tip(exclude_topics=recent)
            cat = "career"
        else:
            ch = self.bot.get_channel(CHANNEL_ETUDES_FORMATIONS)
            recent = get_recent_topics("formation", limit=20)
            text = await generate_formation_guide(exclude_topics=recent)
            cat = "formation"

        if ch and text:
            await ch.send(text)
            title_line = text.split("\n")[0].replace("#", "").strip()
            record_topic(cat, title_line)
            await interaction.followup.send(f"✅ Publication effectuée dans {ch.mention} !", ephemeral=True)
        else:
            await interaction.followup.send("Erreur lors de la génération ou salon introuvable.", ephemeral=True)

    @app_commands.command(name="breaking-test", description="Simule une alerte Breaking News avec Components V2 pour le staff.")
    async def breaking_test_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        staff_ch = self.bot.get_channel(CHANNEL_STAFF_OWNERS)
        if not staff_ch:
            await interaction.followup.send("Salon staff introuvable.", ephemeral=True)
            return

        test_title = "Faille 0-Day Critique CVSS 10.0 découverte affectant les protocoles SSH mondiaux"
        test_summary = "Une vulnérabilité majeure d'exécution de code à distance sans authentification a été identifiée. Les correctifs d'urgence sont en cours de déploiement."
        test_url = "https://nvd.nist.gov"

        embed = discord.Embed(
            title="🚨 [TEST DE SIMULATION] Breaking News Tech Majeure",
            description=(
                f"**Titre :** {test_title}\n\n"
                f"**Résumé :** {test_summary}\n\n"
                f"**Lien :** {test_url}\n\n"
                f"👉 *Choisissez le salon et la mention ci-dessous pour tester l'interface Components V2.*"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="CTRLX Simulation Mode")

        view = BreakingNewsApprovalView(test_title, test_summary, test_url)
        await staff_ch.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Panneau de test envoyé dans {staff_ch.mention} !", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
