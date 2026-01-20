from __future__ import annotations

import random
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands


def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


class Rumors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rumor_adicionar", description="🔒 (Mestre) Adiciona um rumor ou gancho de história.")
    @app_commands.describe(titulo="Título curto", descricao="Descrição do rumor", fonte="Origem do rumor")
    @app_commands.check(is_mestre)
    async def rumor_adicionar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descricao: str,
        fonte: Optional[str] = None,
    ):
        await self.bot.db.execute(
            "INSERT INTO rumores (titulo, descricao, fonte) VALUES (?, ?, ?)",
            (titulo, descricao, fonte),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Rumor registrado.", ephemeral=True)

    @app_commands.command(name="rumor_listar", description="📣 Lista rumores ativos ou usados.")
    @app_commands.describe(status="Filtrar por status (Ativo/Usado)")
    async def rumor_listar(
        self, interaction: discord.Interaction, status: Optional[str] = None
    ):
        status = status.title() if status else None
        query = "SELECT id, titulo, descricao, fonte, status FROM rumores"
        params: List[str] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY id DESC LIMIT 20"

        async with self.bot.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhum rumor encontrado.", ephemeral=True
            )

        linhas = []
        for rumor_id, titulo, descricao, fonte, estado in rows:
            base = f"**[{rumor_id}]** {titulo} — {descricao}"
            if fonte:
                base += f" _(Fonte: {fonte})_"
            base += f" [{estado}]"
            linhas.append(base)

        embed = discord.Embed(
            title="📣 Rumores & Ganchos",
            description="\n".join(linhas),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rumor_sortear", description="🎲 Sorteia um rumor ativo para a sessão.")
    async def rumor_sortear(self, interaction: discord.Interaction):
        async with self.bot.db.execute(
            "SELECT id, titulo, descricao, fonte FROM rumores WHERE status = 'Ativo'"
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhum rumor ativo disponível.", ephemeral=True
            )

        rumor_id, titulo, descricao, fonte = random.choice(rows)
        embed = discord.Embed(
            title=f"🎲 Rumor #{rumor_id}: {titulo}",
            description=descricao,
            color=0xFEE75C,
        )
        if fonte:
            embed.set_footer(text=f"Fonte: {fonte}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rumor_usar", description="🔒 (Mestre) Marca rumor como usado.")
    @app_commands.describe(rumor_id="ID do rumor")
    @app_commands.check(is_mestre)
    async def rumor_usar(self, interaction: discord.Interaction, rumor_id: int):
        cursor = await self.bot.db.execute(
            "UPDATE rumores SET status = 'Usado' WHERE id = ?", (rumor_id,)
        )
        await self.bot.db.commit()

        if cursor.rowcount:
            await interaction.response.send_message("✅ Rumor marcado como usado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Rumor não encontrado.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Rumors(bot))
