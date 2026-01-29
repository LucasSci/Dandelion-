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
            msg = (
                f"⛔ **Acesso Negado**\n"
                f"Esta ficha pertence a <@{self.dono_id}>.\n"
                f"💡 **Você já tem um personagem!** Use `/ficha` para ver o seu ou `/criar_ficha` para criar um novo."
            )
        else:
            msg = (
                f"⛔ **Acesso Negado**\n"
                f"Esta ficha pertence a <@{self.dono_id}>.\n"
                f"✨ **Quer jogar?** Use `/criar_ficha` para começar sua aventura!"
            )

        await interaction.response.send_message(msg, ephemeral=True)
        return False
