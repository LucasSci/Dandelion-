from __future__ import annotations

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands


def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


class NPCs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def npc_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        async with self.bot.db.execute(
            "SELECT nome FROM npc_profiles WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]

    @app_commands.command(name="npc_criar", description="🔒 (Mestre) Cadastra um NPC com personalidade dinâmica.")
    @app_commands.describe(
        nome="Nome do NPC",
        personalidade="Traços de personalidade",
        humor="Tom ou humor predominante",
        habitos="Hábitos ou tiques do NPC",
        voz="Identificador de voz (opcional)",
        observacoes="Anotações adicionais",
    )
    @app_commands.check(is_mestre)
    async def npc_criar(
        self,
        interaction: discord.Interaction,
        nome: str,
        personalidade: str,
        humor: str,
        habitos: str,
        voz: Optional[str] = None,
        observacoes: Optional[str] = None,
    ):
        await self.bot.db.execute(
            """
            INSERT INTO npc_profiles (nome, personalidade, humor, habitos, voz, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nome, personalidade, humor, habitos, voz, observacoes),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ NPC cadastrado.", ephemeral=True)

    @app_commands.command(name="npc_ver", description="📇 Exibe o perfil de um NPC.")
    @app_commands.autocomplete(nome=npc_autocomplete)
    async def npc_ver(self, interaction: discord.Interaction, nome: str):
        async with self.bot.db.execute(
            """
            SELECT personalidade, humor, habitos, voz, observacoes
            FROM npc_profiles WHERE nome = ?
            """,
            (nome,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ NPC não encontrado.", ephemeral=True
            )

        personalidade, humor, habitos, voz, observacoes = row
        embed = discord.Embed(title=f"🧑‍🤝‍🧑 NPC: {nome}", color=0x8E44AD)
        embed.add_field(name="Personalidade", value=personalidade, inline=False)
        embed.add_field(name="Humor", value=humor, inline=False)
        embed.add_field(name="Hábitos", value=habitos, inline=False)
        if voz:
            embed.add_field(name="Voz", value=voz, inline=False)
        if observacoes:
            embed.add_field(name="Observações", value=observacoes, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="npc_falar", description="🗣️ Interage com um NPC usando IA.")
    @app_commands.describe(nome="Nome do NPC", mensagem="O que você diz ao NPC")
    @app_commands.autocomplete(nome=npc_autocomplete)
    async def npc_falar(
        self, interaction: discord.Interaction, nome: str, mensagem: str
    ):
        await interaction.response.defer()

        async with self.bot.db.execute(
            """
            SELECT personalidade, humor, habitos, voz, observacoes
            FROM npc_profiles WHERE nome = ?
            """,
            (nome,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.followup.send("❌ NPC não encontrado.")

        personalidade, humor, habitos, voz, observacoes = row
        ai = self.bot.get_cog("AIHandler")
        if not ai:
            return await interaction.followup.send("❌ IA indisponível no momento.")

        resposta = await ai.gerar_dialogo_npc(
            {
                "nome": nome,
                "personalidade": personalidade,
                "humor": humor,
                "habitos": habitos,
                "voz": voz,
                "observacoes": observacoes,
            },
            mensagem,
        )

        embed = discord.Embed(
            title=f"🗣️ {nome} responde",
            description=resposta,
            color=0x8E44AD,
        )
        if voz:
            embed.set_footer(text=f"Voz sugerida: {voz}")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(NPCs(bot))
