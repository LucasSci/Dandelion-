import discord
from discord import app_commands
from discord.ext import commands

from application.services.solo_campaign_service import SoloCampaignService
from infrastructure.repositories.character_repository import SqliteCharacterRepositoryAdapter
from infrastructure.repositories.solo_repository import SqliteSoloRepositoryAdapter


class SoloCampaign(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.solo_service = SoloCampaignService(
            character_repo=SqliteCharacterRepositoryAdapter(bot.db),
            solo_repo=SqliteSoloRepositoryAdapter(bot.db),
        )

    @app_commands.command(
        name="solo_iniciar",
        description="Inicia uma campanha solo com progresso individual do personagem.",
    )
    @app_commands.describe(gancho="Um gancho inicial para a aventura (opcional).")
    async def solo_iniciar(self, interaction: discord.Interaction, gancho: str | None = None):
        await interaction.response.defer(ephemeral=True)

        existente = await self.solo_service.buscar_resumo_campanha(interaction.user.id)
        if existente:
            local_info = f"📍 Local atual: **{existente.local_nome or 'Desconhecida'}**"
            return await interaction.followup.send(
                "🧭 Sua campanha solo já está ativa.\n"
                f"📖 Capítulo **{existente.capitulo}** — Progresso {existente.progresso}%\n"
                f"{local_info}\n"
                f"🎣 Gancho: {existente.gancho or 'Não definido'}"
            )

        iniciada = await self.solo_service.iniciar_campanha(interaction.user.id, gancho)
        if not iniciada:
            return await interaction.followup.send("❌ Você precisa criar uma ficha antes de iniciar.")

        await interaction.followup.send(
            "✨ Campanha solo iniciada!\n"
            "📖 Capítulo **1** — Progresso 0%\n"
            f"🎣 Gancho: {gancho or 'Não definido'}"
        )

    @app_commands.command(
        name="solo_avancar",
        description="Avança a campanha solo, ganha XP e coleta recursos.",
    )
    @app_commands.describe(passo="Quantidade de avanços (1-5).")
    async def solo_avancar(self, interaction: discord.Interaction, passo: int = 1):
        await interaction.response.defer(ephemeral=True)

        resultado = await self.solo_service.avancar_campanha(interaction.user.id, passo)
        if not resultado:
            return await interaction.followup.send("❌ Você ainda não iniciou uma campanha solo.")

        nivel_msg = ""
        if resultado.niveis_subidos > 0:
            nivel_msg = f"\n🎉 **LEVEL UP!** +{resultado.niveis_subidos} nível(is)."

        local_info = f"📍 Local atual: **{resultado.local_nome or 'Desconhecida'}**"

        await interaction.followup.send(
            "🚶 Você avançou na campanha solo!\n"
            f"📖 Capítulo **{resultado.capitulo}** — Progresso {resultado.progresso}%\n"
            f"{local_info}\n"
            f"✨ XP ganho: **{resultado.xp_ganho}** (XP atual: {resultado.xp_restante}){nivel_msg}\n"
            f"🎒 Recurso coletado: **{resultado.recurso_qtd}x {resultado.recurso_nome}**"
        )

    @app_commands.command(
        name="solo_diario",
        description="Mostra as últimas entradas da campanha solo.",
    )
    async def solo_diario(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        entradas = await self.solo_service.listar_entradas_diario(interaction.user.id, limit=5)
        if not entradas:
            return await interaction.followup.send("📖 Ainda não há entradas no diário solo.")

        descricao = "\n".join(
            f"**Cap. {capitulo}** — {texto} ({criado_em})" for capitulo, texto, criado_em in entradas
        )
        embed = discord.Embed(
            title="📖 Diário da Campanha Solo",
            description=descricao,
            color=0x2B2D31,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="solo_recursos",
        description="Exibe os recursos coletados na campanha solo.",
    )
    async def solo_recursos(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        recursos = await self.solo_service.listar_recursos(interaction.user.id)
        if not recursos:
            return await interaction.followup.send("🎒 Nenhum recurso coletado ainda.")

        descricao = "\n".join(f"• **{nome}** — {quantidade}" for nome, quantidade in recursos)
        embed = discord.Embed(
            title="🎒 Recursos da Campanha Solo",
            description=descricao,
            color=0x2B2D31,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SoloCampaign(bot))
