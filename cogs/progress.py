from __future__ import annotations

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands


def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


class Progress(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def faccao_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        async with self.bot.db.execute(
            "SELECT nome FROM faccoes WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]

    async def conquista_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        async with self.bot.db.execute(
            "SELECT nome FROM conquistas WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]

    @app_commands.command(name="faccao_criar", description="🔒 (Mestre) Cria uma facção.")
    @app_commands.describe(nome="Nome da facção", descricao="Descrição da facção")
    @app_commands.check(is_mestre)
    async def faccao_criar(self, interaction: discord.Interaction, nome: str, descricao: str):
        await self.bot.db.execute(
            "INSERT INTO faccoes (nome, descricao) VALUES (?, ?)", (nome, descricao)
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Facção criada.", ephemeral=True)

    @app_commands.command(name="faccao_listar", description="🏛️ Lista facções registradas.")
    async def faccao_listar(self, interaction: discord.Interaction):
        async with self.bot.db.execute(
            "SELECT nome, descricao FROM faccoes ORDER BY nome"
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhuma facção registrada.", ephemeral=True
            )

        linhas = [f"**{nome}** — {descricao}" for nome, descricao in rows]
        embed = discord.Embed(
            title="🏛️ Facções",
            description="\n".join(linhas),
            color=0x1ABC9C,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reputacao_definir", description="🔒 (Mestre) Define reputação com uma facção.")
    @app_commands.autocomplete(faccao=faccao_autocomplete)
    @app_commands.check(is_mestre)
    async def reputacao_definir(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        faccao: str,
        valor: int,
    ):
        async with self.bot.db.execute(
            "SELECT id FROM faccoes WHERE nome = ?", (faccao,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ Facção não encontrada.", ephemeral=True
            )

        faccao_id = row[0]
        await self.bot.db.execute(
            """
            INSERT INTO reputacoes (user_id, faccao_id, reputacao)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, faccao_id)
            DO UPDATE SET reputacao = excluded.reputacao, atualizado_em = datetime('now')
            """,
            (usuario.id, faccao_id, valor),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Reputação atualizada.", ephemeral=True)

    @app_commands.command(name="reputacao_ver", description="📊 Vê reputações de um jogador.")
    async def reputacao_ver(
        self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None
    ):
        alvo = usuario or interaction.user
        async with self.bot.db.execute(
            """
            SELECT f.nome, r.reputacao
            FROM reputacoes r
            JOIN faccoes f ON f.id = r.faccao_id
            WHERE r.user_id = ?
            ORDER BY f.nome
            """,
            (alvo.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhuma reputação registrada.", ephemeral=True
            )

        linhas = [f"**{nome}**: {rep}" for nome, rep in rows]
        embed = discord.Embed(
            title=f"📊 Reputação de {alvo.display_name}",
            description="\n".join(linhas),
            color=0x1ABC9C,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="conquista_criar", description="🔒 (Mestre) Registra uma conquista.")
    @app_commands.check(is_mestre)
    async def conquista_criar(
        self, interaction: discord.Interaction, nome: str, descricao: str, categoria: str
    ):
        await self.bot.db.execute(
            "INSERT INTO conquistas (nome, descricao, categoria) VALUES (?, ?, ?)",
            (nome, descricao, categoria),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Conquista registrada.", ephemeral=True)

    @app_commands.command(name="conquista_dar", description="🔒 (Mestre) Concede uma conquista a um jogador.")
    @app_commands.autocomplete(conquista=conquista_autocomplete)
    @app_commands.check(is_mestre)
    async def conquista_dar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        conquista: str,
    ):
        async with self.bot.db.execute(
            "SELECT id FROM conquistas WHERE nome = ?", (conquista,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ Conquista não encontrada.", ephemeral=True
            )

        conquista_id = row[0]
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO usuario_conquistas (user_id, conquista_id) VALUES (?, ?)",
            (usuario.id, conquista_id),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("🏅 Conquista concedida!", ephemeral=True)

    @app_commands.command(name="conquistas_ver", description="🏅 Lista conquistas de um jogador.")
    async def conquistas_ver(
        self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None
    ):
        alvo = usuario or interaction.user
        async with self.bot.db.execute(
            """
            SELECT c.nome, c.descricao, c.categoria
            FROM usuario_conquistas uc
            JOIN conquistas c ON c.id = uc.conquista_id
            WHERE uc.user_id = ?
            ORDER BY uc.obtido_em DESC
            """,
            (alvo.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhuma conquista registrada.", ephemeral=True
            )

        linhas = [f"**{nome}** ({categoria}) — {descricao}" for nome, descricao, categoria in rows]
        embed = discord.Embed(
            title=f"🏅 Conquistas de {alvo.display_name}",
            description="\n".join(linhas),
            color=0xF1C40F,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="legado_adicionar", description="🔒 (Mestre) Registra legado de campanhas anteriores.")
    @app_commands.check(is_mestre)
    async def legado_adicionar(
        self, interaction: discord.Interaction, usuario: discord.Member, titulo: str, descricao: str
    ):
        await self.bot.db.execute(
            "INSERT INTO legado_beneficios (user_id, titulo, descricao) VALUES (?, ?, ?)",
            (usuario.id, titulo, descricao),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Legado registrado.", ephemeral=True)

    @app_commands.command(name="legado_ver", description="🧬 Exibe legados do jogador.")
    async def legado_ver(
        self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None
    ):
        alvo = usuario or interaction.user
        async with self.bot.db.execute(
            "SELECT titulo, descricao FROM legado_beneficios WHERE user_id = ?",
            (alvo.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhum legado registrado.", ephemeral=True
            )

        linhas = [f"**{titulo}** — {descricao}" for titulo, descricao in rows]
        embed = discord.Embed(
            title=f"🧬 Legados de {alvo.display_name}",
            description="\n".join(linhas),
            color=0x9B59B6,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="comparar_builds", description="⚖️ Compara atributos entre dois personagens.")
    async def comparar_builds(
        self, interaction: discord.Interaction, jogador_a: discord.Member, jogador_b: discord.Member
    ):
        async with self.bot.db.execute(
            """
            SELECT nome, nivel, hp_max, mp_max, ataque, defesa
            FROM personagens WHERE user_id = ?
            """,
            (jogador_a.id,),
        ) as cursor:
            a_row = await cursor.fetchone()

        async with self.bot.db.execute(
            """
            SELECT nome, nivel, hp_max, mp_max, ataque, defesa
            FROM personagens WHERE user_id = ?
            """,
            (jogador_b.id,),
        ) as cursor:
            b_row = await cursor.fetchone()

        if not a_row or not b_row:
            return await interaction.response.send_message(
                "❌ Ambos os jogadores precisam ter ficha.", ephemeral=True
            )

        a_nome, a_nivel, a_hp, a_mp, a_atk, a_def = a_row
        b_nome, b_nivel, b_hp, b_mp, b_atk, b_def = b_row

        def linha(label: str, a: int, b: int) -> str:
            seta = "="
            if a > b:
                seta = "↑"
            elif b > a:
                seta = "↓"
            return f"{label}: {a} {seta} {b}"

        comparativo = "\n".join(
            [
                linha("Nível", a_nivel, b_nivel),
                linha("HP", a_hp, b_hp),
                linha("MP", a_mp, b_mp),
                linha("Ataque", a_atk, b_atk),
                linha("Defesa", a_def, b_def),
            ]
        )

        embed = discord.Embed(
            title="⚖️ Comparador de Builds",
            description=f"**{a_nome}** vs **{b_nome}**\n\n{comparativo}",
            color=0xE67E22,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="atributos_sugerir", description="🧭 Sugere pesos de atributos por papel.")
    @app_commands.choices(
        papel=[
            app_commands.Choice(name="Tanque", value="Tanque"),
            app_commands.Choice(name="Dano", value="Dano"),
            app_commands.Choice(name="Suporte", value="Suporte"),
            app_commands.Choice(name="Controle", value="Controle"),
            app_commands.Choice(name="Explorador", value="Explorador"),
        ]
    )
    async def atributos_sugerir(self, interaction: discord.Interaction, papel: str):
        sugestões = {
            "Tanque": "HP > Defesa > Ataque > MP",
            "Dano": "Ataque > MP > Defesa > HP",
            "Suporte": "MP > Defesa > HP > Ataque",
            "Controle": "MP > Defesa > Ataque > HP",
            "Explorador": "Defesa > Ataque > HP > MP",
        }
        sugestao = sugestões.get(papel, "HP > Defesa > Ataque > MP")
        await interaction.response.send_message(
            f"🔧 Para **{papel}**, priorize: **{sugestao}**", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Progress(bot))
