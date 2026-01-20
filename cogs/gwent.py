import random

import discord
from discord import app_commands
from discord.ext import commands


GWENT_RISCO = {
    "casual": {"label": "Casual", "multiplier": 1.0, "npc_bonus": 0},
    "profissional": {"label": "Profissional", "multiplier": 1.5, "npc_bonus": 2},
    "alto_risco": {"label": "Alto risco", "multiplier": 2.0, "npc_bonus": 3},
}


class Gwent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gwent", description="🃏 Dispute Gwent e ganhe ouro")
    @app_commands.describe(
        aposta="Valor da aposta (5-200).",
        risco="Define o nível de risco e recompensa.",
    )
    @app_commands.choices(risco=[
        app_commands.Choice(name="Casual (x1)", value="casual"),
        app_commands.Choice(name="Profissional (x1.5)", value="profissional"),
        app_commands.Choice(name="Alto risco (x2)", value="alto_risco"),
    ])
    @app_commands.checks.cooldown(1, 1800)
    async def gwent(
        self,
        interaction: discord.Interaction,
        aposta: app_commands.Range[int, 5, 200] = 20,
        risco: str = "casual",
    ):
        db = self.bot.db
        async with db.execute(
            "SELECT ouro, nivel FROM personagens WHERE user_id = ?",
            (interaction.user.id,),
        ) as cursor:
            dados = await cursor.fetchone()

        if not dados:
            return await interaction.response.send_message(
                "❌ Você precisa de uma ficha para jogar.",
                ephemeral=True,
            )

        ouro_atual, nivel = dados
        if aposta > ouro_atual:
            return await interaction.response.send_message(
                f"💸 Ouro insuficiente. Seu saldo atual é {ouro_atual}G.",
                ephemeral=True,
            )

        config = GWENT_RISCO.get(risco, GWENT_RISCO["casual"])
        player_bonus = min(2, nivel // 5)
        npc_bonus = config["npc_bonus"]

        vitorias_player = 0
        vitorias_npc = 0
        rodadas = []

        for indice in range(1, 4):
            player_score = random.randint(1, 10) + player_bonus
            npc_score = random.randint(1, 10) + npc_bonus

            if player_score > npc_score:
                resultado = "✅"
                vitorias_player += 1
            elif npc_score > player_score:
                resultado = "❌"
                vitorias_npc += 1
            else:
                resultado = "⚖️"

            rodadas.append(
                f"R{indice}: {resultado} **{player_score}** x **{npc_score}**"
            )

        if vitorias_player > vitorias_npc:
            resultado_final = "Vitória"
            delta_ouro = int(aposta * config["multiplier"])
        elif vitorias_npc > vitorias_player:
            resultado_final = "Derrota"
            delta_ouro = -aposta
        else:
            resultado_final = "Empate"
            delta_ouro = 0

        if delta_ouro != 0:
            await db.execute(
                "UPDATE personagens SET ouro = ouro + ? WHERE user_id = ?",
                (delta_ouro, interaction.user.id),
            )
            await db.commit()

        novo_ouro = ouro_atual + delta_ouro
        variacao = f"{'+' if delta_ouro >= 0 else ''}{delta_ouro}G"

        embed = discord.Embed(
            title="🃏 Gwent",
            description=f"**{resultado_final}** | {variacao}",
            color=0x1abc9c if delta_ouro >= 0 else 0xe74c3c,
        )
        embed.add_field(
            name="Aposta",
            value=f"{aposta}G",
            inline=True,
        )
        embed.add_field(
            name="Risco",
            value=f"{config['label']} (x{config['multiplier']})",
            inline=True,
        )
        embed.add_field(
            name="Bônus",
            value=f"Você +{player_bonus} | Oponente +{npc_bonus}",
            inline=False,
        )
        embed.add_field(name="Rodadas", value="\n".join(rodadas), inline=False)
        embed.set_footer(text=f"Saldo atual: {novo_ouro}G")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Gwent(bot))
