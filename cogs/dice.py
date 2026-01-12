import random
import re
import discord
from discord.ext import commands
from discord import app_commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Autocomplete para dados
    async def dados_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        opcoes = ["1d20", "1d20+5", "2d20", "1d6", "2d6", "3d6", "1d8", "1d10", "1d100"]
        return [
            app_commands.Choice(name=opcao, value=opcao)
            for opcao in opcoes if current.lower() in opcao.lower()
        ]

    @app_commands.command(name="rolar", description="🎲 Rola dados")
    @app_commands.autocomplete(formula=dados_autocomplete) # <--- AQUI
    async def rolar(self, interaction: discord.Interaction, formula: str):
        formula = formula.lower().replace(" ", "")
        match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', formula)

        if not match:
            return await interaction.response.send_message("❌ Fórmula inválida. Ex: `1d20+5`", ephemeral=True)

        qtd, lados, sinal, bonus = match.groups()
        qtd, lados = int(qtd), int(lados)
        bonus = int(bonus) if bonus else 0

        if qtd > 50: return await interaction.response.send_message("⚠️ Máximo de 50 dados.", ephemeral=True)

        rolls = [random.randint(1, lados) for _ in range(qtd)]
        total = sum(rolls) + (bonus if sinal == "+" else -bonus)
        
        rolls_fmt = [f"**🌟{r}**" if lados==20 and r==20 else f"**💀{r}**" if lados==20 and r==1 else str(r) for r in rolls]
        
        embed = discord.Embed(title="🎲 Resultado", color=0x2b2d31)
        embed.description = f"[{', '.join(rolls_fmt)}] {'+' if sinal=='+' else '-'} {bonus}" if bonus else f"[{', '.join(rolls_fmt)}]"
        embed.add_field(name="Total", value=f"# **{total}**")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dice(bot))