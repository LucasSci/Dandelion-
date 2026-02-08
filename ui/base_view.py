import discord
from discord import ui

from utils.i18n import get_interaction_context


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

        has_char = False
        try:
            async with interaction.client.db.execute(
                "SELECT 1 FROM personagens WHERE user_id = ? LIMIT 1",
                (interaction.user.id,)
            ) as cursor:
                has_char = await cursor.fetchone() is not None
        except Exception:
            # Fallback seguro caso haja erro no banco
            pass

        if has_char:
            ctx = get_interaction_context(interaction)
            msg = ctx.t("ui.access_denied.has_character", owner_id=self.dono_id)
        else:
            ctx = get_interaction_context(interaction)
            msg = ctx.t("ui.access_denied.no_character", owner_id=self.dono_id)

        await interaction.response.send_message(msg, ephemeral=True)
        return False
