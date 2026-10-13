import discord
from discord import app_commands, ui
from discord.ext import commands
import time
import logging
from config import ROLE_REVIEWER_ACTIF, ROLE_TOP_REVIEWER, CHANNEL_VOS_PROJETS
from database import (
    record_feedback_transaction,
    get_last_feedback_given_time,
    get_feedback_leaderboard,
    get_ships_leaderboard
)

logger = logging.getLogger("CTRLX.FeedbackCog")

class FeedbackLauncherView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Classement Top Reviewers", style=discord.ButtonStyle.secondary, emoji="🏆", custom_id="ctrlx_fb_lead_karma")
    async def lead_karma_btn(self, interaction: discord.Interaction, button: ui.Button):
        items = get_feedback_leaderboard(limit=10)
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        embed = discord.Embed(
            title="🏆 Classement Karma d'Entraide • Top Reviewers",
            description="Les membres les plus engagés qui testent et donnent du retour constructif sur les projets des autres.",
            color=0xE67E22
        )
        if not items:
            embed.add_field(name="Aucune donnée enregistrée", value="Soyez le premier à tester un projet avec `/feedback-thank` !", inline=False)
        else:
            lines = [f"{medals[i] if i < len(medals) else f'`#{i+1}`'} <@{r['user_id']}> : **{r['feedback_karma']} pts de Karma**" for i, r in enumerate(items)]
            embed.add_field(name="Top 10 Membres", value="\n".join(lines), inline=False)
        embed.set_footer(text="CTRLX Community • Émulation et Entraide")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Classement Top Builders", style=discord.ButtonStyle.secondary, emoji="🚀", custom_id="ctrlx_fb_lead_ships")
    async def lead_ships_btn(self, interaction: discord.Interaction, button: ui.Button):
        items = get_ships_leaderboard(limit=10)
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        embed = discord.Embed(
            title="🚀 Classement des Builders • Projets Livrés",
            description="Les créateurs les plus réguliers qui expédient des fonctionnalités et avancées dans ship-log.",
            color=0x3498DB
        )
        if not items:
            embed.add_field(name="Aucune donnée enregistrée", value="Soyez le premier à poster dans `ship-log` !", inline=False)
        else:
            lines = [f"{medals[i] if i < len(medals) else f'`#{i+1}`'} <@{r['user_id']}> : **{r['ships_count']} ships livrés**" for i, r in enumerate(items)]
            embed.add_field(name="Top 10 Membres", value="\n".join(lines), inline=False)
        embed.set_footer(text="CTRLX Community • Émulation et Entraide")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Valider ce feedback (+1 Karma)",
            callback=self.context_reward_feedback
        )
        self.bot.tree.add_command(self.ctx_menu)
        self.bot.add_view(FeedbackLauncherView())

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def check_and_assign_karma_roles(self, member: discord.Member, new_karma: int):
        if not member.guild:
            return

        try:
            if new_karma >= 15:
                top_role = member.guild.get_role(ROLE_TOP_REVIEWER)
                if top_role and top_role not in member.roles:
                    await member.add_roles(top_role)
            elif new_karma >= 5:
                active_role = member.guild.get_role(ROLE_REVIEWER_ACTIF)
                if active_role and active_role not in member.roles:
                    await member.add_roles(active_role)
        except Exception as e:
            logger.debug(f"Error updating karma roles: {e}")

    @app_commands.command(name="feedback-thank", description="Attribue +1 Karma à un membre ayant testé ou fait un retour utile sur votre projet.")
    @app_commands.describe(
        membre="Le membre qui vous a aidé ou a testé votre projet",
        raison="Ce qui vous a été utile dans son retour"
    )
    async def feedback_thank_cmd(self, interaction: discord.Interaction, membre: discord.User | discord.Member, raison: str = "Retour constructif sur le projet"):
        if membre.id == interaction.user.id:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous attribuer du Karma à vous-même !", ephemeral=True)
            return

        if membre.bot:
            await interaction.response.send_message("❌ Vous ne pouvez pas attribuer de Karma à un bot.", ephemeral=True)
            return

        last_given = get_last_feedback_given_time(interaction.user.id)
        if time.time() - last_given < 60:
            remaining = int(60 - (time.time() - last_given))
            await interaction.response.send_message(f"⏳ Veuillez patienter encore {remaining}s avant de récompenser un autre membre.", ephemeral=True)
            return

        new_karma = record_feedback_transaction(
            giver_id=interaction.user.id,
            receiver_id=membre.id,
            channel_id=interaction.channel_id or 0,
            reason=raison
        )

        if isinstance(membre, discord.Member):
            await self.check_and_assign_karma_roles(membre, new_karma)

        embed = discord.Embed(
            title="🌟 Feedback Récompensé !",
            description=(
                f"{interaction.user.mention} a validé le retour de {membre.mention} et lui a attribué **+1 point de Karma d'Entraide** !\n\n"
                f"💬 **Raison :** *{raison}*\n"
                f"📈 **Nouveau solde :** `{new_karma} pts de Karma`"
            ),
            color=0xE67E22
        )
        embed.set_footer(text="CTRLX Économie du Feedback • Donnez pour recevoir")
        await interaction.response.send_message(embed=embed)

    async def context_reward_feedback(self, interaction: discord.Interaction, message: discord.Message):
        target_author = message.author
        if target_author.id == interaction.user.id:
            await interaction.response.send_message("❌ Vous ne pouvez pas récompenser votre propre message.", ephemeral=True)
            return

        if target_author.bot:
            await interaction.response.send_message("❌ Impossible de récompenser un bot.", ephemeral=True)
            return

        last_given = get_last_feedback_given_time(interaction.user.id)
        if time.time() - last_given < 60:
            remaining = int(60 - (time.time() - last_given))
            await interaction.response.send_message(f"⏳ Veuillez patienter encore {remaining}s avant de récompenser un autre message.", ephemeral=True)
            return

        reason_preview = message.clean_content[:80] or "Retour constructif"
        new_karma = record_feedback_transaction(
            giver_id=interaction.user.id,
            receiver_id=target_author.id,
            message_id=message.id,
            channel_id=message.channel.id,
            reason=reason_preview
        )

        if isinstance(target_author, discord.Member):
            await self.check_and_assign_karma_roles(target_author, new_karma)

        embed = discord.Embed(
            title="🌟 Feedback Validé !",
            description=(
                f"{interaction.user.mention} a récompensé le message de {target_author.mention} avec **+1 Karma d'Entraide** !\n\n"
                f"💬 **Extrait du feedback :** *\"{reason_preview}\"*\n"
                f"📈 **Nouveau solde :** `{new_karma} pts de Karma`"
            ),
            color=0xE67E22
        )
        embed.set_footer(text="CTRLX Économie du Feedback • Donnez pour recevoir")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Consultez le classement des meilleurs contributeurs et builders CTRLX.")
    @app_commands.describe(categorie="Choisissez le classement à afficher")
    @app_commands.choices(categorie=[
        app_commands.Choice(name="🌟 Karma d'Entraide (Top Reviewers)", value="karma"),
        app_commands.Choice(name="🔨 Ships & Projets Livrés (Top Builders)", value="ships")
    ])
    async def leaderboard_cmd(self, interaction: discord.Interaction, categorie: str = "karma"):
        await interaction.response.defer()

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        if categorie == "karma":
            items = get_feedback_leaderboard(limit=10)
            title = "🏆 Classement Karma d'Entraide • Top Reviewers"
            desc = "Les membres les plus engagés qui testent et donnent du retour constructif sur les projets des autres."
            color = 0xE67E22
        else:
            items = get_ships_leaderboard(limit=10)
            title = "🚀 Classement des Builders • Projets Livrés"
            desc = "Les créateurs les plus réguliers qui expédient des fonctionnalités et avancées dans ship-log."
            color = 0x3498DB

        embed = discord.Embed(title=title, description=desc, color=color)

        if not items:
            embed.add_field(
                name="Aucune donnée enregistrée",
                value="Soyez le premier à tester un projet avec `/feedback-thank` ou à poster dans `ship-log` !",
                inline=False
            )
        else:
            lines = []
            for idx, row in enumerate(items):
                u_id = row.get("user_id", 0)
                medal = medals[idx] if idx < len(medals) else f"`#{idx+1}`"
                if categorie == "karma":
                    pts = row.get("feedback_karma", 0)
                    lines.append(f"{medal} <@{u_id}> : **{pts} pts de Karma**")
                else:
                    ships = row.get("ships_count", 0)
                    lines.append(f"{medal} <@{u_id}> : **{ships} ships livrés**")

            embed.add_field(name="Top 10 Membres", value="\n".join(lines), inline=False)

        embed.set_footer(text="CTRLX Community • Émulation et Entraide")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="feedback-panel", description="Affiche le panneau explicatif de l'économie du feedback dans le salon.")
    @app_commands.default_permissions(administrator=True)
    async def feedback_panel_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💡 L'Économie du Feedback sur CTRLX",
            description=(
                "Ici, aucun projet ne reste sans réponse. Le principe est simple : **Donnez du feedback pour en recevoir en retour.**\n\n"
                "### 🎯 Comment ça marche ?\n"
                "• **Testez un projet :** Allez dans <#1433173347830857839> ou <#1504831943307432086> et écrivez un retour constructif (UX, bugs, perf, clarté).\n"
                "• **Gagnez du Karma :** L'auteur du projet clique-droit sur votre message > **Apps** > `Valider ce feedback (+1 Karma)` ou tape `/feedback-thank`.\n"
                "• **Montez de niveau :** Débloquez les rôles `@⭐ Reviewer Actif` (5 pts) et `@💎 Top Reviewer` (15 pts) visibles sur votre `/profile`.\n"
                "• **Mise en avant :** Les meilleurs contributeurs figurent sur le `/leaderboard` et leurs projets sont prioritairement mis en avant !"
            ),
            color=0xF39C12
        )
        embed.set_footer(text="CTRLX • Build in Public & Entraide")
        view = FeedbackLauncherView()
        await interaction.response.send_message("Panneau envoyé !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(FeedbackCog(bot))
