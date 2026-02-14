import discord
from discord import app_commands
from discord.ext import commands
from ui.guide_view import GuideView

class Guide(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ajuda", description="📖 Guia interativo do Dandelion")
    async def ajuda(self, interaction: discord.Interaction):
        view = GuideView()
        embed = view.get_embed("home")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Guide(bot))
