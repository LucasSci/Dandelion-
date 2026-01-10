import random
import re
import discord
from discord.ext import commands
from discord import app_commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolar", description="🎲 Rola dados de RPG")
    async def rolar(self, interaction: discord.Interaction, formula: str):
        formula = formula.lower().replace(" ", "")
        match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', formula)

        if not match:
            return await interaction.response.send_message(
                "❌ Fórmula inválida. Ex: `1d20+5`",
                ephemeral=True
            )

        qtd, lados, sinal, bonus = match.groups()
        qtd, lados = int(qtd), int(lados)
        bonus = int(bonus) if bonus else 0

        if qtd > 50:
            return await interaction.response.send_message(
                "⚠️ Máximo de 50 dados.",
                ephemeral=True
            )

        rolls = [random.randint(1, lados) for _ in range(qtd)]
        total = sum(rolls) + (bonus if sinal == "+" else -bonus)

        embed = discord.Embed(
            title="🎲 RESULTADO",
            description=f"`{rolls}`",
            color=0x2b2d31
        )
        embed.add_field(name="Total", value=f"**{total}**")

        await interaction.response.send_message(embed=embed)
async def setup(bot):
    await bot.add_cog(Dice(bot))    