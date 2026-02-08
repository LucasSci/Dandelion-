from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


@dataclass(frozen=True)
class TicketTriage:
    categoria: str
    prioridade: str
    notas: str


def _infer_sentiment(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    if score >= 8:
        return "positivo"
    if score >= 5:
        return "neutro"
    return "negativo"


def _triage_ticket(texto: str) -> TicketTriage:
    texto_lower = texto.lower()
    prioridade = "Média"
    categoria = "Geral"
    notas = []

    if any(k in texto_lower for k in ("erro", "bug", "falha", "crash", "travou", "quebrou")):
        categoria = "Bug"
        prioridade = "Alta"
        notas.append("Detectado relato de erro/bug.")
    if any(k in texto_lower for k in ("lento", "performance", "lag", "demora")):
        categoria = "Performance"
        prioridade = "Média" if prioridade != "Alta" else prioridade
        notas.append("Possível problema de performance.")
    if any(k in texto_lower for k in ("pagamento", "cobran", "fatura", "pix")):
        categoria = "Cobrança"
        prioridade = "Alta"
        notas.append("Indícios de cobrança/pagamento.")
    if any(k in texto_lower for k in ("ideia", "sugest", "feature", "melhoria")):
        categoria = "Sugestão"
        prioridade = "Baixa" if prioridade != "Alta" else prioridade
        notas.append("Solicitação de melhoria/feature.")
    if any(k in texto_lower for k in ("ajuda", "suporte", "não consigo", "dúvida")):
        categoria = "Suporte"
        prioridade = "Média" if prioridade != "Alta" else prioridade
        notas.append("Pedido de ajuda/suporte.")

    if not notas:
        notas.append("Triagem automática sem sinal forte. Revisão manual recomendada.")

    return TicketTriage(categoria=categoria, prioridade=prioridade, notas=" ".join(notas))


class FeedbackSupport(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _track_usage(self, interaction: discord.Interaction, status: str) -> None:
        if not self.bot.db:
            return
        command_name = interaction.command.qualified_name if interaction.command else "desconhecido"
        await self.bot.db.execute(
            """
            INSERT INTO usage_events (user_id, guild_id, channel_id, command_name, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id if interaction.user else None,
                interaction.guild_id,
                interaction.channel_id,
                command_name,
                status,
            ),
        )
        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command) -> None:
        await self._track_usage(interaction, "sucesso")

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        await self._track_usage(interaction, "erro")

    @app_commands.command(name="feedback", description="📣 Enviar feedback geral sobre o bot")
    @app_commands.describe(
        tipo="Tipo de feedback",
        comentario="Detalhes adicionais",
        nota="Nota opcional (0-10)",
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Geral", value="geral"),
            app_commands.Choice(name="UX/UI", value="ui"),
            app_commands.Choice(name="Performance", value="performance"),
            app_commands.Choice(name="Suporte", value="suporte"),
            app_commands.Choice(name="Bug", value="bug"),
        ]
    )
    async def feedback(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
        comentario: str,
        nota: Optional[int] = None,
    ) -> None:
        if nota is not None and (nota < 0 or nota > 10):
            return await interaction.response.send_message("⚠️ A nota deve ser entre 0 e 10.", ephemeral=True)

        sentiment = _infer_sentiment(nota)
        await self.bot.db.execute(
            """
            INSERT INTO feedback_entries (user_id, guild_id, channel_id, feedback_type, score, sentiment, comentario, contexto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                tipo.value,
                nota,
                sentiment,
                comentario,
                "feedback",
            ),
        )
        await self.bot.db.commit()

        await interaction.response.send_message("✅ Feedback enviado! Obrigado por ajudar a melhorar o Dandelion.", ephemeral=True)

    @app_commands.command(name="nps", description="⭐ Avalie com NPS (0-10)")
    @app_commands.describe(
        nota="0 a 10",
        comentario="Opcional: conte o porquê da nota",
    )
    async def nps(self, interaction: discord.Interaction, nota: int, comentario: Optional[str] = None) -> None:
        if nota < 0 or nota > 10:
            return await interaction.response.send_message("⚠️ A nota deve ser entre 0 e 10.", ephemeral=True)

        sentiment = _infer_sentiment(nota)
        await self.bot.db.execute(
            """
            INSERT INTO feedback_entries (user_id, guild_id, channel_id, feedback_type, score, sentiment, comentario, contexto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                "nps",
                nota,
                sentiment,
                comentario,
                "nps",
            ),
        )
        await self.bot.db.commit()

        await interaction.response.send_message("🙏 Obrigado! Sua avaliação NPS foi registrada.", ephemeral=True)

    @app_commands.command(name="satisfacao", description="😊 Registre sua satisfação (1-5)")
    @app_commands.describe(
        nota="1 (ruim) a 5 (ótimo)",
        comentario="Opcional: detalhes",
    )
    async def satisfacao(
        self,
        interaction: discord.Interaction,
        nota: int,
        comentario: Optional[str] = None,
    ) -> None:
        if nota < 1 or nota > 5:
            return await interaction.response.send_message("⚠️ A nota deve ser entre 1 e 5.", ephemeral=True)

        sentimento = "positivo" if nota >= 4 else "neutro" if nota == 3 else "negativo"
        await self.bot.db.execute(
            """
            INSERT INTO feedback_entries (user_id, guild_id, channel_id, feedback_type, score, sentiment, comentario, contexto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                "satisfacao",
                nota,
                sentimento,
                comentario,
                "satisfacao",
            ),
        )
        await self.bot.db.commit()

        await interaction.response.send_message("✅ Satisfação registrada. Valeu pelo retorno!", ephemeral=True)

    @app_commands.command(name="ticket_abrir", description="🆘 Abrir um ticket de suporte")
    @app_commands.describe(
        titulo="Resumo do problema",
        descricao="Detalhe o que está acontecendo",
    )
    async def ticket_abrir(
        self,
        interaction: discord.Interaction,
        titulo: str,
        descricao: str,
    ) -> None:
        triagem = _triage_ticket(f"{titulo}\n{descricao}")
        await self.bot.db.execute(
            """
            INSERT INTO support_tickets (
                user_id, guild_id, channel_id, titulo, descricao, categoria, prioridade, status, triagem_notas
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Aberto', ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                titulo,
                descricao,
                triagem.categoria,
                triagem.prioridade,
                triagem.notas,
            ),
        )
        await self.bot.db.commit()

        embed = discord.Embed(
            title="🎫 Ticket criado",
            description="Sua solicitação foi registrada. A equipe fará a triagem final.",
            color=0x5865F2,
        )
        embed.add_field(name="Categoria sugerida", value=triagem.categoria, inline=True)
        embed.add_field(name="Prioridade", value=triagem.prioridade, inline=True)
        embed.add_field(name="Notas de triagem", value=triagem.notas, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="relatorio_uso", description="📊 Relatório de uso de comandos")
    @app_commands.describe(dias="Quantos dias para incluir")
    @app_commands.checks.has_permissions(administrator=True)
    async def relatorio_uso(self, interaction: discord.Interaction, dias: Optional[int] = 7) -> None:
        if dias is None or dias <= 0:
            return await interaction.response.send_message("⚠️ Informe um número de dias válido.", ephemeral=True)

        since = datetime.utcnow() - timedelta(days=dias)
        async with self.bot.db.execute(
            """
            SELECT command_name, status, COUNT(*)
            FROM usage_events
            WHERE criado_em >= ?
            GROUP BY command_name, status
            ORDER BY COUNT(*) DESC
            """,
            (since.strftime("%Y-%m-%d %H:%M:%S"),),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message("📭 Nenhum evento encontrado no período.", ephemeral=True)

        linhas = []
        for command_name, status, total in rows:
            linhas.append(f"• `{command_name}` — {status}: **{total}**")

        embed = discord.Embed(
            title="📊 Relatório de uso",
            description="\n".join(linhas)[:4000],
            color=0x2ECC71,
        )
        embed.set_footer(text=f"Últimos {dias} dias")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeedbackSupport(bot))
