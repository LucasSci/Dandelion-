import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DB_NAME = "bestiario.db"

class Skills(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="usar_habilidade")
    async def usar_habilidade(self, interaction: discord.Interaction, slot: int):
        if slot not in range(1, 5):
            return await interaction.response.send_message("Use slots de 1 a 4.", ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as conn:
            async with conn.execute("""
                SELECT h.nome, h.efeito
                FROM habilidades_disponiveis h
                JOIN slots_equipados s ON h.id = s.habilidade_id
                WHERE s.user_id = ? AND s.numero_slot = ?
            """, (interaction.user.id, slot)) as cursor:
                habilidade = await cursor.fetchone()

        if not habilidade:
            return await interaction.response.send_message("❌ Slot vazio.", ephemeral=True)

        nome, efeito = habilidade
        await interaction.response.send_message(
            f"✨ **{interaction.user.display_name}** usou **{nome}**!\n*{efeito}*"
        )

async def setup(bot):
    await bot.add_cog(Skills(bot))