import discord
import logging
from config import (
    CHANNEL_TECH_RADAR, CHANNEL_OFF_TOPIC, CHANNEL_TECH_TALK,
    ROLE_VEILLE_TECH
)
from database import mark_item_posted, increment_metric

logger = logging.getLogger("CTRLX.Views")

class EditAlertModal(discord.ui.Modal, title="Modifier l'Alerte Breaking News"):
    def __init__(self, current_text: str, parent_view: 'BreakingNewsApprovalView'):
        super().__init__()
        self.parent_view = parent_view
        self.custom_content = discord.ui.TextInput(
            label="Contenu du message à publier",
            style=discord.TextStyle.paragraph,
            default=current_text,
            max_length=1900,
            required=True
        )
        self.add_item(self.custom_content)

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.custom_text = self.custom_content.value
        await interaction.response.send_message("Texte personnalisé enregistré pour la diffusion !", ephemeral=True)

class ChannelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📺・tech-radar", value=str(CHANNEL_TECH_RADAR), description="Salon de veille officiel (Recommandé)", default=True),
            discord.SelectOption(label="☕・off-topic", value=str(CHANNEL_OFF_TOPIC), description="Salon détente (Actu historique)"),
            discord.SelectOption(label="🗨️・tech-talk", value=str(CHANNEL_TECH_TALK), description="Salon discussions techniques")
        ]
        super().__init__(placeholder="Choisir le salon de destination...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.target_channel_id = int(self.values[0])
        for opt in self.options:
            opt.default = (opt.value == self.values[0])
        await interaction.response.edit_message(view=self.view)

class MentionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📺 Rôle Veille Tech (Opt-in)", value="role", description="Mentionne uniquement les intéressés", default=True),
            discord.SelectOption(label="🚨 @everyone", value="everyone", description="Notification générale"),
            discord.SelectOption(label="🔔 @here", value="here", description="Notification des membres connectés"),
            discord.SelectOption(label="🔇 Aucune mention", value="none", description="Publication discrète sans ping")
        ]
        super().__init__(placeholder="Choisir la mention...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.mention_type = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == self.values[0])
        await interaction.response.edit_message(view=self.view)

class BreakingNewsApprovalView(discord.ui.View):
    def __init__(self, title: str, summary: str, url: str):
        super().__init__(timeout=None)
        self.alert_title = title
        self.alert_summary = summary
        self.alert_url = url
        self.custom_text = ""
        self.target_channel_id = CHANNEL_TECH_RADAR
        self.mention_type = "role"

        self.add_item(ChannelSelect())
        self.add_item(MentionSelect())

    @discord.ui.button(label="Valider & Diffuser", style=discord.ButtonStyle.success, emoji="🚀", row=2)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_channel = interaction.guild.get_channel(self.target_channel_id)
        if not target_channel:
            await interaction.response.send_message(f"Salon cible `{self.target_channel_id}` introuvable.", ephemeral=True)
            return

        mention_str = ""
        if self.mention_type == "everyone":
            mention_str = "@everyone "
        elif self.mention_type == "here":
            mention_str = "@here "
        elif self.mention_type == "role":
            mention_str = f"<@&{ROLE_VEILLE_TECH}> "

        if self.custom_text:
            final_message = f"{mention_str}\n{self.custom_text}"
        else:
            final_message = (
                f"{mention_str}🚨 **BREAKING NEWS TECH : {self.alert_title}**\n\n"
                f"{self.alert_summary}\n\n"
                f"🔗 Source officielle : <{self.alert_url}>"
            )

        try:
            await target_channel.send(final_message)
            mark_item_posted("breaking", self.alert_url, self.alert_title, self.alert_url)
            increment_metric("posts_breaking_approved")

            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(content=f"✅ **Alerte diffusée avec succès** dans {target_channel.mention} par {interaction.user.mention} !", view=self)
        except Exception as e:
            logger.error(f"Error posting breaking news: {e}")
            await interaction.response.send_message(f"Erreur lors de l'envoi : {e}", ephemeral=True)

    @discord.ui.button(label="Modifier le texte", style=discord.ButtonStyle.secondary, emoji="✏️", row=2)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        default_val = self.custom_text or f"🚨 **BREAKING NEWS TECH : {self.alert_title}**\n\n{self.alert_summary}\n\n🔗 Source : <{self.alert_url}>"
        modal = EditAlertModal(default_val, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Rejeter l'alerte", style=discord.ButtonStyle.danger, emoji="✖️", row=2)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"❌ **Alerte rejetée** par {interaction.user.mention}.", view=self)

class SocialStudioView(discord.ui.View):
    def __init__(self, post_data: dict):
        super().__init__(timeout=None)
        self.post_data = post_data

    @discord.ui.button(label="Copier LinkedIn", style=discord.ButtonStyle.primary, emoji="💼")
    async def copy_linkedin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"**Format LinkedIn :**\n```markdown\n{self.post_data.get('linkedin', '')}\n```", ephemeral=True)

    @discord.ui.button(label="Copier X (Twitter)", style=discord.ButtonStyle.primary, emoji="🐦")
    async def copy_twitter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"**Format X :**\n```markdown\n{self.post_data.get('twitter', '')}\n```", ephemeral=True)

    @discord.ui.button(label="Copier Reddit", style=discord.ButtonStyle.primary, emoji="👽")
    async def copy_reddit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"**Format Reddit :**\n```markdown\n{self.post_data.get('reddit', '')}\n```", ephemeral=True)

    @discord.ui.button(label="Marqué comme publié", style=discord.ButtonStyle.success, emoji="✅")
    async def mark_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = f"Publié par {interaction.user.name}"
        await interaction.response.edit_message(view=self)
