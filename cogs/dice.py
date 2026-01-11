import random
import re
import discord
from discord.ext import commands
from discord import app_commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolar", description="🎲 Rola dados de RPG (Ex: 1d20+5)")
    async def rolar(self, interaction: discord.Interaction, formula: str):
        formula = formula.lower().replace(" ", "")
        match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', formula)

        if not match:
            return await interaction.response.send_message(
                "❌ Fórmula inválida. Ex: `1d20+5`", ephemeral=True
            )

        qtd, lados, sinal, bonus = match.groups()
        qtd, lados = int(qtd), int(lados)
        bonus = int(bonus) if bonus else 0

        if qtd > 50:
            return await interaction.response.send_message("⚠️ Máximo de 50 dados.", ephemeral=True)

        rolls = [random.randint(1, lados) for _ in range(qtd)]
        soma_dados = sum(rolls)
        total = soma_dados + (bonus if sinal == "+" else -bonus)

        # Formatação Visual
        rolls_fmt = []
        for r in rolls:
            if lados == 20 and r == 20:
                rolls_fmt.append(f"**🌟{r}**") # Crítico
            elif lados == 20 and r == 1:
                rolls_fmt.append(f"**💀{r}**") # Falha
            else:
                rolls_fmt.append(str(r))
        
        rolls_str = ", ".join(rolls_fmt)

        embed = discord.Embed(title="🎲 Resultado", color=0x2b2d31)
        embed.description = f"Dados: [{rolls_str}]"
        if bonus:
            op = "+" if sinal == "+" else "-"
            embed.description += f" {op} {bonus}"
        
        embed.add_field(name="Total", value=f"# **{total}**")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dice(bot))