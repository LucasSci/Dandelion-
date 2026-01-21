import random

import discord
from discord import app_commands
from discord.ext import commands

from data.repositories import CharacterRepository, SoloRepository

RESOURCE_POOL = [
    ("Ervas Medicinais", (1, 3)),
    ("Couro de Monstro", (1, 2)),
    ("Minério Bruto", (1, 2)),
    ("Componentes Alquímicos", (1, 2)),
    ("Fragmentos Antigos", (1, 1)),
]


class SoloCampaign(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.character_repo = CharacterRepository(bot.db)
        self.solo_repo = SoloRepository(bot.db)

    def _gerar_recompensas(self, passo: int) -> tuple[int, tuple[str, int]]:
        passo = max(1, min(passo, 5))
        xp_ganho = random.randint(30, 80) * passo
        recurso_nome, (min_qtd, max_qtd) = random.choice(RESOURCE_POOL)
        recurso_qtd = random.randint(min_qtd, max_qtd) * passo
        return xp_ganho, (recurso_nome, recurso_qtd)

    async def _aplicar_xp(self, user_id: int, xp: int) -> tuple[int, int]:
        dados = await self.character_repo.fetch_progress_by_user(user_id)
        if not dados:
            return 0, 0

        nivel, xp_atual, hp_max, hp_atual, ataque = dados
        if hp_atual is None:
            hp_atual = hp_max

        xp_atual += xp
        niveis_subidos = 0

        while True:
            xp_necessario = nivel * 1000
            if xp_atual >= xp_necessario:
                xp_atual -= xp_necessario
                nivel += 1
                hp_max += 5
                hp_atual += 5
                ataque += 1
                niveis_subidos += 1
            else:
                break

        await self.character_repo.update_progress(user_id, nivel, xp_atual, hp_max, hp_atual, ataque)
        return niveis_subidos, xp_atual

    @app_commands.command(
        name="solo_iniciar",
        description="Inicia uma campanha solo com progresso individual do personagem.",
    )
    @app_commands.describe(gancho="Um gancho inicial para a aventura (opcional).")
    async def solo_iniciar(self, interaction: discord.Interaction, gancho: str | None = None):
        await interaction.response.defer(ephemeral=True)

        personagem_info = await self.character_repo.fetch_character_id_and_location(interaction.user.id)
        if not personagem_info:
            return await interaction.followup.send("❌ Você precisa criar uma ficha antes de iniciar.")

        existente = await self.solo_repo.fetch_campaign(interaction.user.id)
        if existente:
            _, _, capitulo, progresso, gancho_atual, _, local_nome, _ = existente
            local_info = f"📍 Local atual: **{local_nome or 'Desconhecida'}**"
            return await interaction.followup.send(
                "🧭 Sua campanha solo já está ativa.\n"
                f"📖 Capítulo **{capitulo}** — Progresso {progresso}%\n"
                f"{local_info}\n"
                f"🎣 Gancho: {gancho_atual or 'Não definido'}"
            )

        personagem_id, localizacao_id = personagem_info
        await self.solo_repo.create_campaign(interaction.user.id, personagem_id, gancho, localizacao_id)
        await self.solo_repo.add_story_entry(
            interaction.user.id,
            1,
            "Início da jornada solo. O mundo se abre diante do personagem.",
        )

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

        campanha = await self.solo_repo.fetch_campaign(interaction.user.id)
        if not campanha:
            return await interaction.followup.send("❌ Você ainda não iniciou uma campanha solo.")

        passo = max(1, min(passo, 5))
        _, _, capitulo, progresso, _, _, _, _ = campanha
        progresso_ganho = passo * 20
        progresso_atual = progresso + progresso_ganho
        capitulo_novo = capitulo
        if progresso_atual >= 100:
            capitulo_novo += progresso_atual // 100
            progresso_atual = progresso_atual % 100

        personagem_info = await self.character_repo.fetch_character_id_and_location(interaction.user.id)
        if not personagem_info:
            return await interaction.followup.send("❌ Não encontrei sua ficha para atualizar o progresso.")
        localizacao_id = personagem_info[1] if personagem_info else None
        await self.solo_repo.update_campaign(interaction.user.id, capitulo_novo, progresso_atual, localizacao_id)

        xp_ganho, (recurso_nome, recurso_qtd) = self._gerar_recompensas(passo)
        niveis_subidos, xp_restante = await self._aplicar_xp(interaction.user.id, xp_ganho)
        await self.solo_repo.upsert_resource(interaction.user.id, recurso_nome, recurso_qtd)

        await self.solo_repo.add_story_entry(
            interaction.user.id,
            capitulo_novo,
            f"Avanço na jornada: +{xp_ganho} XP, +{recurso_qtd} {recurso_nome}.",
        )

        nivel_msg = ""
        if niveis_subidos > 0:
            nivel_msg = f"\n🎉 **LEVEL UP!** +{niveis_subidos} nível(is)."

        local_row = await self.character_repo.fetch_location_by_user(interaction.user.id)
        local_nome = local_row[1] if local_row else None
        local_info = f"📍 Local atual: **{local_nome or 'Desconhecida'}**"

        await interaction.followup.send(
            "🚶 Você avançou na campanha solo!\n"
            f"📖 Capítulo **{capitulo_novo}** — Progresso {progresso_atual}%\n"
            f"{local_info}\n"
            f"✨ XP ganho: **{xp_ganho}** (XP atual: {xp_restante}){nivel_msg}\n"
            f"🎒 Recurso coletado: **{recurso_qtd}x {recurso_nome}**"
        )

    @app_commands.command(
        name="solo_diario",
        description="Mostra as últimas entradas da campanha solo.",
    )
    async def solo_diario(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        entradas = await self.solo_repo.list_story_entries(interaction.user.id, limit=5)
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

        recursos = await self.solo_repo.list_resources(interaction.user.id)
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
