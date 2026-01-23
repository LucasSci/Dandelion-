import discord
from discord import ui


class BaseRPGView(ui.View):
    def __init__(self, bot, user_id_dono, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.dono_id = user_id_dono

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.dono_id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            f"⛔ **Você não pode interagir aqui!**\n\nEsta ficha pertence a <@{self.dono_id}>. Use `/criar_ficha` para criar o seu personagem.",
            ephemeral=True
        )
        return False
