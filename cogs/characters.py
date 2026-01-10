import sqlite3
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

        with sqlite3.connect(DB_NAME) as conn:
            res = conn.execute("""
                SELECT nome, raca, classe, nivel, historia, imagem_url
                FROM personagens
                WHERE user_id = ?
            """, (target.id,)).fetchone()

        if not res:
            return await interaction.response.send_message(
                "❌ Ficha não encontrada.",
                ephemeral=True
            )

        nome, raca, classe, nivel, historia, img = res

        embed = discord.Embed(title=nome, color=0x2b2d31)
        embed.add_field(name="Raça", value=raca)
        embed.add_field(name="Classe", value=classe)
        embed.add_field(name="Nível", value=nivel)
        embed.description = historia or "Sem história registrada."

        if img:
            embed.set_thumbnail(url=img)

        await interaction.response.send_message(embed=embed)
