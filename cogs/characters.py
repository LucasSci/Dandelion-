import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands
from ui.modals import CriarFichaModal

DB_NAME = "bestiario.db"

class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ficha_criar")
    async def ficha_criar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CriarFichaModal())

    @app_commands.command(name="ficha")
    async def ficha(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("""
                SELECT nome, raca, classe, nivel, historia, imagem_url, ouro
                FROM personagens
                WHERE user_id = ?
            """, (target.id,)) as cursor:
                res = await cursor.fetchone()

        if not res:
            return await interaction.response.send_message(
                "❌ Ficha não encontrada. Use /ficha_criar",
                ephemeral=True
            )

        # Desempacota considerando a coluna ouro (se existir no select)
        if len(res) == 7:
            nome, raca, classe, nivel, historia, img, ouro = res
        else:
            nome, raca, classe, nivel, historia, img = res
            ouro = 0

        embed = discord.Embed(title=nome, color=0x2b2d31)
        embed.add_field(name="Raça", value=raca)
        embed.add_field(name="Classe", value=classe)
        embed.add_field(name="Nível", value=str(nivel))
        embed.add_field(name="Ouro", value=f"💰 {ouro}")
        embed.description = historia or "Sem história registrada."

        if img:
            embed.set_thumbnail(url=img)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Characters(bot))