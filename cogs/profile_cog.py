import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from config import (
    ROLE_DEV_WEB, ROLE_DEV_MOBILE, ROLE_WEB3,
    ROLE_CYBER, ROLE_HARDWARE, ROLE_IA_DATA, ROLE_SYSTEMS_CLOUD
)
from database import get_user_profile, upsert_user_profile

logger = logging.getLogger("CTRLX.ProfileCog")

DOMAIN_ROLES = {
    "Web": ("🌐 Dev Web & Fullstack", ROLE_DEV_WEB),
    "Mobile": ("📱 Dev Mobile", ROLE_DEV_MOBILE),
    "Web3": ("⛓️ Web3 & Blockchain", ROLE_WEB3),
    "Cyber": ("🔒 Cybersécurité", ROLE_CYBER),
    "Hardware": ("⚙️ Hardware & IoT", ROLE_HARDWARE),
    "AI": ("🧠 IA & Data Science", ROLE_IA_DATA),
    "Cloud": ("🖥️ Cloud & DevOps", ROLE_SYSTEMS_CLOUD)
}

class ProfileModal(ui.Modal, title="Configurer votre profil CTRLX"):
    speciality = ui.TextInput(
        label="Spécialité / Métier",
        placeholder="Ex: Dev Fullstack, Pentesteur, Ingénieur Embarqué...",
        max_length=80,
        required=True
    )
    skills = ui.TextInput(
        label="Stack & Technologies clés",
        placeholder="Ex: Python, Rust, Next.js, Docker, Flipper Zero...",
        max_length=120,
        required=True
    )
    github_url = ui.TextInput(
        label="Lien GitHub",
        placeholder="https://github.com/votre-pseudo",
        max_length=100,
        required=False
    )
    portfolio_url = ui.TextInput(
        label="Portfolio / Site web",
        placeholder="https://votre-site.dev",
        max_length=100,
        required=False
    )
    bio = ui.TextInput(
        label="Bio courte",
        placeholder="Ce que vous aimez construire ou explorer...",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )

    def __init__(self, current_profile: dict, selected_domains: list[str]):
        super().__init__()
        self.selected_domains = selected_domains
        if current_profile.get("speciality"):
            self.speciality.default = current_profile["speciality"]
        if current_profile.get("skills"):
            self.skills.default = current_profile["skills"]
        if current_profile.get("github_url"):
            self.github_url.default = current_profile["github_url"]
        if current_profile.get("portfolio_url"):
            self.portfolio_url.default = current_profile["portfolio_url"]
        if current_profile.get("bio"):
            self.bio.default = current_profile["bio"]

    async def on_submit(self, interaction: discord.Interaction):
        domains_str = ", ".join(self.selected_domains) if self.selected_domains else "Généraliste"
        upsert_user_profile(
            user_id=interaction.user.id,
            domains=domains_str,
            speciality=self.speciality.value,
            skills=self.skills.value,
            github_url=self.github_url.value,
            portfolio_url=self.portfolio_url.value,
            bio=self.bio.value
        )

        if isinstance(interaction.user, discord.Member) and interaction.guild:
            for key in self.selected_domains:
                if key in DOMAIN_ROLES:
                    _, role_id = DOMAIN_ROLES[key]
                    role = interaction.guild.get_role(role_id)
                    if role and role not in interaction.user.roles:
                        try:
                            await interaction.user.add_roles(role)
                        except Exception as e:
                            logger.debug(f"Could not assign domain role {role_id}: {e}")

        await interaction.response.send_message("✅ Votre profil CTRLX a été mis à jour avec succès !", ephemeral=True)

class DomainSelectView(ui.View):
    def __init__(self, current_profile: dict):
        super().__init__(timeout=180)
        self.current_profile = current_profile

    @ui.select(
        placeholder="Choisissez vos domaines d'expertise principaux...",
        min_values=1,
        max_values=4,
        options=[
            discord.SelectOption(label="Dev Web & Fullstack", value="Web", emoji="🌐"),
            discord.SelectOption(label="Dev Mobile (iOS/Android)", value="Mobile", emoji="📱"),
            discord.SelectOption(label="Web3 & Smart Contracts", value="Web3", emoji="⛓️"),
            discord.SelectOption(label="Cybersécurité & Pentest", value="Cyber", emoji="🔒"),
            discord.SelectOption(label="Hardware, IoT & Embarqué", value="Hardware", emoji="⚙️"),
            discord.SelectOption(label="IA & Data Science", value="AI", emoji="🧠"),
            discord.SelectOption(label="Cloud, Systèmes & DevOps", value="Cloud", emoji="🖥️")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: ui.Select):
        modal = ProfileModal(self.current_profile, select.values)
        await interaction.response.send_modal(modal)

class ProfileCardView(ui.View):
    def __init__(self, profile: dict, viewer_id: int):
        super().__init__(timeout=None)
        self.profile = profile
        self.viewer_id = viewer_id

        if profile.get("github_url"):
            gh_url = profile["github_url"]
            if not gh_url.startswith("http"):
                gh_url = f"https://{gh_url}"
            self.add_item(ui.Button(label="GitHub", url=gh_url, emoji="🐙"))

        if profile.get("portfolio_url"):
            port_url = profile["portfolio_url"]
            if not port_url.startswith("http"):
                port_url = f"https://{port_url}"
            self.add_item(ui.Button(label="Portfolio / Site", url=port_url, emoji="🌐"))

        if profile.get("user_id") == viewer_id:
            edit_btn = ui.Button(label="Modifier mon profil", style=discord.ButtonStyle.secondary, emoji="✏️", custom_id="profile_quick_edit")
            edit_btn.callback = self.edit_callback
            self.add_item(edit_btn)

    async def edit_callback(self, interaction: discord.Interaction):
        current = get_user_profile(interaction.user.id)
        view = DomainSelectView(current)
        await interaction.response.send_message("Choisissez d'abord vos domaines pour mettre à jour votre profil :", view=view, ephemeral=True)

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Voir le profil CTRLX",
            callback=self.context_view_profile
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    def build_profile_embed(self, user: discord.User | discord.Member, profile: dict) -> discord.Embed:
        speciality = profile.get("speciality") or "Membre de la communauté"
        domains = profile.get("domains") or "Non renseigné"
        skills = profile.get("skills") or "Non renseigné"
        bio = profile.get("bio") or "Aucune biographie rédigée pour le moment."
        karma = profile.get("feedback_karma", 0)
        ships = profile.get("ships_count", 0)

        if karma >= 15:
            rank_karma = "💎 Top Reviewer"
        elif karma >= 5:
            rank_karma = "⭐ Reviewer Actif"
        elif karma >= 1:
            rank_karma = "🌱 Contributeur"
        else:
            rank_karma = "Novice"

        if ships >= 10:
            rank_ships = "⚡ Serial Builder"
        elif ships >= 3:
            rank_ships = "🔨 Builder Vérifié"
        elif ships >= 1:
            rank_ships = "🚀 Initié"
        else:
            rank_ships = "Explorateur"

        embed = discord.Embed(
            title=f"Profil Développeur • {user.display_name}",
            description=f"*{speciality}*\n\n{bio}",
            color=0x2ECC71 if karma > 0 else 0x3498DB
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="🏷️ Domaines", value=f"`{domains}`", inline=False)
        embed.add_field(name="🛠️ Stack & Compétences", value=f"`{skills}`", inline=False)

        stats_value = (
            f"• **Karma Feedback :** `{karma} pts` ({rank_karma})\n"
            f"• **Ships livrés :** `{ships} projets` ({rank_ships})"
        )
        embed.add_field(name="📊 Émulation & Réputation", value=stats_value, inline=False)
        embed.set_footer(text="CTRLX Community • Carte de compétences")
        return embed

    @app_commands.command(name="profile", description="Affiche la fiche profil et le portfolio d'un membre CTRLX.")
    @app_commands.describe(membre="Membre dont vous souhaitez consulter le profil (par défaut vous-même)")
    async def profile_cmd(self, interaction: discord.Interaction, membre: discord.User | discord.Member = None):
        target = membre or interaction.user
        profile = get_user_profile(target.id)
        embed = self.build_profile_embed(target, profile)
        view = ProfileCardView(profile, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="profile-edit", description="Configure ou met à jour votre profil et vos domaines de compétences.")
    async def profile_edit_cmd(self, interaction: discord.Interaction):
        profile = get_user_profile(interaction.user.id)
        view = DomainSelectView(profile)
        await interaction.response.send_message(
            "Sélectionnez vos domaines d'expertise pour ouvrir l'éditeur de profil :",
            view=view,
            ephemeral=True
        )

    async def context_view_profile(self, interaction: discord.Interaction, user: discord.User | discord.Member):
        profile = get_user_profile(user.id)
        embed = self.build_profile_embed(user, profile)
        view = ProfileCardView(profile, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
