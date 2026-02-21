from __future__ import annotations

import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI


class ForumSession(commands.Cog):
    forum_rpg = app_commands.Group(
        name="forum_rpg",
        description="Fluxo de RPG de fórum com geração por IA + moderação do mestre.",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    @staticmethod
    def _is_mestre(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    async def _buscar_contexto(self, session_id: int, user_id: int) -> str:
        contexto = []

        async with self.bot.db.execute(
            """
            SELECT p.nome, p.raca, p.classe, p.historia, wl.nome
            FROM personagens p
            LEFT JOIN world_locations wl ON wl.id = p.localizacao_id
            WHERE p.user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ) as c:
            personagem = await c.fetchone()

        if personagem:
            nome, raca, classe, historia, local = personagem
            contexto.append(
                f"PERSONAGEM: {nome} ({raca or 'desconhecida'} / {classe or 'sem classe'}) | "
                f"Local: {local or 'indefinido'} | História: {(historia or '').strip()[:220]}"
            )

        async with self.bot.db.execute(
            """
            SELECT titulo, COALESCE(resumo, conteudo)
            FROM lore_entries
            ORDER BY atualizado_em DESC
            LIMIT 5
            """
        ) as c:
            lores = await c.fetchall()

        if lores:
            contexto.append(
                "LORE: "
                + " | ".join(
                    f"{titulo}: {(texto or '').strip()[:160]}" for titulo, texto in lores
                )
            )

        async with self.bot.db.execute(
            """
            SELECT id, decisao_jogador, COALESCE(texto_final, texto_ia)
            FROM forum_session_posts
            WHERE session_id = ? AND status = 'aprovado'
            ORDER BY id DESC
            LIMIT 4
            """,
            (session_id,),
        ) as c:
            ultimos_posts = await c.fetchall()

        if ultimos_posts:
            ultimos_posts.reverse()
            linhas = [
                f"#{pid} Decisão: {decisao[:100]} | Resultado: {resultado[:140]}"
                for pid, decisao, resultado in ultimos_posts
            ]
            contexto.append("CRONOLOGIA RECENTE: " + " || ".join(linhas))

        return "\n".join(contexto)

    async def _gerar_texto(self, decisao: str, contexto: str) -> str:
        if not self.client:
            return (
                "A decisão do jogador altera o rumo da cena. "
                f"Com base em '{decisao}', a narrativa avança respeitando os fatos do mundo. "
                "Surgem consequências imediatas, um obstáculo coerente e um novo gancho para o próximo post."
            )

        prompt = (
            "Você é narrador de RPG de fórum. Gere APENAS o próximo post em português brasileiro. "
            "Regras: manter continuidade, respeitar lore/contexto, não invalidar decisões prévias, "
            "propor consequências plausíveis e terminar com 2-3 opções de continuidade para o jogador.\n\n"
            f"CONTEXTO:\n{contexto}\n\n"
            f"DECISÃO DO JOGADOR:\n{decisao}"
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return (
                "Não foi possível consultar a IA neste momento. "
                "Use o rascunho manual do mestre para continuar a sessão."
            )

    @forum_rpg.command(name="iniciar", description="Cria uma sessão de RPG de fórum moderada.")
    @app_commands.describe(
        titulo="Nome da sessão.",
        descricao="Resumo da proposta narrativa.",
        canal_publicacao="Canal onde posts aprovados serão publicados.",
    )
    async def iniciar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descricao: str,
        canal_publicacao: Optional[discord.TextChannel] = None,
    ):
        if not self._is_mestre(interaction):
            return await interaction.response.send_message(
                "❌ Apenas o mestre (admin) pode iniciar sessões de fórum.",
                ephemeral=True,
            )

        guild_id = interaction.guild_id or 0
        canal_id = canal_publicacao.id if canal_publicacao else interaction.channel_id
        cur = await self.bot.db.execute(
            """
            INSERT INTO forum_sessions (guild_id, canal_publicacao_id, titulo, descricao, master_id, status)
            VALUES (?, ?, ?, ?, ?, 'ativa')
            """,
            (guild_id, canal_id, titulo, descricao, interaction.user.id),
        )
        await self.bot.db.commit()

        await interaction.response.send_message(
            f"✅ Sessão criada! ID **{cur.lastrowid}**. Jogadores podem entrar com `/forum_rpg entrar`."
        )

    @forum_rpg.command(name="entrar", description="Entra em uma sessão ativa como jogador.")
    @app_commands.describe(sessao_id="ID da sessão.")
    async def entrar(self, interaction: discord.Interaction, sessao_id: int):
        async with self.bot.db.execute(
            "SELECT id, status FROM forum_sessions WHERE id = ?",
            (sessao_id,),
        ) as c:
            sessao = await c.fetchone()

        if not sessao or sessao[1] != "ativa":
            return await interaction.response.send_message("❌ Sessão não encontrada ou inativa.", ephemeral=True)

        async with self.bot.db.execute(
            "SELECT id, nome FROM personagens WHERE user_id = ? LIMIT 1",
            (interaction.user.id,),
        ) as c:
            personagem = await c.fetchone()

        personagem_id = personagem[0] if personagem else None
        personagem_nome = personagem[1] if personagem else None

        await self.bot.db.execute(
            """
            INSERT INTO forum_session_participants (session_id, user_id, personagem_id, personagem_nome)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, user_id)
            DO UPDATE SET personagem_id=excluded.personagem_id, personagem_nome=excluded.personagem_nome
            """,
            (sessao_id, interaction.user.id, personagem_id, personagem_nome),
        )
        await self.bot.db.commit()

        await interaction.response.send_message("✅ Você entrou na sessão e já pode usar `/forum_rpg decidir`.", ephemeral=True)

    @forum_rpg.command(name="decidir", description="Envia decisão do jogador e gera rascunho por IA para moderação.")
    @app_commands.describe(sessao_id="ID da sessão.", decisao="Ação tomada pelo jogador.")
    async def decidir(self, interaction: discord.Interaction, sessao_id: int, decisao: str):
        await interaction.response.defer(ephemeral=True)

        async with self.bot.db.execute(
            "SELECT id FROM forum_session_participants WHERE session_id = ? AND user_id = ?",
            (sessao_id, interaction.user.id),
        ) as c:
            participante = await c.fetchone()

        if not participante:
            return await interaction.followup.send("❌ Você não faz parte desta sessão.")

        contexto = await self._buscar_contexto(sessao_id, interaction.user.id)
        texto_ia = await self._gerar_texto(decisao, contexto)

        cur = await self.bot.db.execute(
            """
            INSERT INTO forum_session_posts (session_id, user_id, decisao_jogador, contexto_geracao, texto_ia, status)
            VALUES (?, ?, ?, ?, ?, 'pendente')
            """,
            (sessao_id, interaction.user.id, decisao, contexto, texto_ia),
        )
        await self.bot.db.commit()

        embed = discord.Embed(
            title=f"📝 Rascunho IA #{cur.lastrowid} (pendente de moderação)",
            description=texto_ia[:3900],
            color=0xF1C40F,
        )
        embed.add_field(name="Decisão", value=decisao[:1024], inline=False)
        embed.set_footer(text="O mestre precisa aprovar, editar ou rejeitar antes da publicação.")
        await interaction.followup.send(embed=embed)

    @forum_rpg.command(name="fila", description="Lista posts pendentes para o mestre moderar.")
    @app_commands.describe(sessao_id="ID da sessão.")
    async def fila(self, interaction: discord.Interaction, sessao_id: int):
        if not self._is_mestre(interaction):
            return await interaction.response.send_message("❌ Apenas o mestre pode moderar a fila.", ephemeral=True)

        async with self.bot.db.execute(
            """
            SELECT id, user_id, decisao_jogador, criado_em
            FROM forum_session_posts
            WHERE session_id = ? AND status = 'pendente'
            ORDER BY id ASC
            LIMIT 10
            """,
            (sessao_id,),
        ) as c:
            pendentes = await c.fetchall()

        if not pendentes:
            return await interaction.response.send_message("📭 Não há posts pendentes nesta sessão.", ephemeral=True)

        linhas = [
            f"**#{pid}** • <@{uid}> • {decisao[:80]}... ({criado_em})"
            for pid, uid, decisao, criado_em in pendentes
        ]
        await interaction.response.send_message("\n".join(linhas), ephemeral=True)

    @forum_rpg.command(name="moderar", description="Aprova, edita ou rejeita um rascunho gerado por IA.")
    @app_commands.describe(
        post_id="ID do post gerado.",
        acao="aprovar, editar ou rejeitar.",
        texto_mestre="Texto final (obrigatório para editar).",
        observacao="Motivo/observação da moderação.",
    )
    @app_commands.choices(
        acao=[
            app_commands.Choice(name="aprovar", value="aprovar"),
            app_commands.Choice(name="editar", value="editar"),
            app_commands.Choice(name="rejeitar", value="rejeitar"),
        ]
    )
    async def moderar(
        self,
        interaction: discord.Interaction,
        post_id: int,
        acao: app_commands.Choice[str],
        texto_mestre: Optional[str] = None,
        observacao: Optional[str] = None,
    ):
        if not self._is_mestre(interaction):
            return await interaction.response.send_message("❌ Apenas o mestre pode moderar.", ephemeral=True)

        async with self.bot.db.execute(
            """
            SELECT p.session_id, p.user_id, p.texto_ia, s.canal_publicacao_id
            FROM forum_session_posts p
            JOIN forum_sessions s ON s.id = p.session_id
            WHERE p.id = ? AND p.status = 'pendente'
            """,
            (post_id,),
        ) as c:
            row = await c.fetchone()

        if not row:
            return await interaction.response.send_message("❌ Post não encontrado ou já moderado.", ephemeral=True)

        session_id, user_id, texto_ia, canal_publicacao_id = row

        if acao.value == "editar" and not texto_mestre:
            return await interaction.response.send_message("❌ Informe `texto_mestre` para editar.", ephemeral=True)

        if acao.value == "rejeitar":
            await self.bot.db.execute(
                """
                UPDATE forum_session_posts
                SET status = 'rejeitado', observacao_mestre = ?, moderado_por = ?, moderado_em = datetime('now')
                WHERE id = ?
                """,
                (observacao, interaction.user.id, post_id),
            )
            await self.bot.db.commit()
            return await interaction.response.send_message("🛑 Post rejeitado.", ephemeral=True)

        texto_final = texto_mestre if acao.value == "editar" else texto_ia
        await self.bot.db.execute(
            """
            UPDATE forum_session_posts
            SET status = 'aprovado', texto_final = ?, observacao_mestre = ?, moderado_por = ?, moderado_em = datetime('now')
            WHERE id = ?
            """,
            (texto_final, observacao, interaction.user.id, post_id),
        )
        await self.bot.db.commit()

        canal = self.bot.get_channel(canal_publicacao_id) if canal_publicacao_id else interaction.channel
        if not isinstance(canal, discord.TextChannel):
            canal = interaction.channel

        embed = discord.Embed(
            title=f"📜 Sessão #{session_id} • Post aprovado",
            description=texto_final[:3900],
            color=0x2ECC71,
        )
        embed.set_footer(text=f"Post #{post_id} • Jogador <@{user_id}>")

        await canal.send(embed=embed)
        await interaction.response.send_message("✅ Post aprovado e publicado no canal da sessão.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ForumSession(bot))
