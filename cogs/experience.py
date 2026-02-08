from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List

import discord
from discord import app_commands
from discord.ext import commands

from data.repositories import CharacterRepository
from ui.design_system import DEFAULT_THEME, build_section_lines, themed_embed


DASHBOARD_LAYOUT_DEFAULT = ["resumo", "atalhos", "inventario", "quests", "campanha"]
DASHBOARD_LAYOUT_OPTIONS = {
    "resumo": "Resumo do personagem",
    "atalhos": "Atalhos principais",
    "inventario": "Inventário recente",
    "quests": "Quests e contratos",
    "campanha": "Progresso de campanha solo",
    "combate": "Status de combate",
}


@dataclass(frozen=True)
class OnboardingStep:
    title: str
    description: str
    actions: Iterable[str]


ONBOARDING_STEPS: List[OnboardingStep] = [
    OnboardingStep(
        title="Bem-vindo ao Dandelion",
        description="Você está prestes a montar sua primeira ficha e começar a campanha.",
        actions=("Use `/criar_ficha` para criar o personagem.", "Defina raça, classe e imagem."),
    ),
    OnboardingStep(
        title="Painel do personagem",
        description="O painel reúne atributos, combate, magia e inventário em um só lugar.",
        actions=("Abra `/ficha` para navegar pelas abas.", "Clique em *Geral* para ver o resumo."),
    ),
    OnboardingStep(
        title="Inventário e recursos",
        description="Controle itens, poções e ouro com clareza.",
        actions=("Use `/inventario` para revisar os itens.", "No painel, acesse a aba *Inventário*."),
    ),
    OnboardingStep(
        title="Combate e rolagens",
        description="As ações de combate seguem o padrão de botões e respostas.",
        actions=("Participe de um combate com `/combate_entrar`.", "Use `/rolar` para testes rápidos."),
    ),
    OnboardingStep(
        title="Pronto para a aventura",
        description="Ative o seu dashboard para acompanhar tudo em tempo real.",
        actions=("Abra `/dashboard` e personalize as seções.", "Retorne quando quiser com `/onboarding`."),
    ),
]


class OnboardingView(discord.ui.View):
    def __init__(self, steps: List[OnboardingStep]):
        super().__init__(timeout=300)
        self.steps = steps
        self.index = 0

    def _build_embed(self) -> discord.Embed:
        step = self.steps[self.index]
        embed = themed_embed(f"{DEFAULT_THEME.tokens.emojis['onboarding']} {step.title}", variant="info")
        embed.description = step.description
        embed.add_field(name="✅ Próximos passos", value="\n".join(f"• {action}" for action in step.actions), inline=False)
        embed.set_footer(text=f"Etapa {self.index + 1}/{len(self.steps)} • Navegação guiada")
        return embed

    async def _update(self, interaction: discord.Interaction) -> None:
        self.btn_prev.disabled = self.index == 0
        self.btn_next.disabled = self.index >= len(self.steps) - 1
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await self._update(interaction)

    @discord.ui.button(label="Avançar", style=discord.ButtonStyle.primary, emoji="➡️")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(len(self.steps) - 1, self.index + 1)
        await self._update(interaction)

    @discord.ui.button(label="Concluir", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_done(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✨ Onboarding concluído! Volte quando quiser com `/onboarding`.",
            embed=None,
            view=None,
        )
        self.stop()


class DashboardLayoutSelect(discord.ui.Select):
    def __init__(self, current_layout: Iterable[str]):
        options = [
            discord.SelectOption(
                label=title,
                value=key,
                description=DASHBOARD_LAYOUT_OPTIONS[key],
                default=key in current_layout,
            )
            for key, title in [
                ("resumo", "Resumo"),
                ("atalhos", "Atalhos"),
                ("inventario", "Inventário"),
                ("quests", "Quests"),
                ("campanha", "Campanha"),
                ("combate", "Combate"),
            ]
        ]
        super().__init__(
            placeholder="Selecione as seções do dashboard",
            min_values=1,
            max_values=len(options),
            options=options,
        )


class DashboardView(discord.ui.View):
    def __init__(self, cog: "Experience", user_id: int, layout: Iterable[str]):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.layout = list(layout)

    async def _refresh(self, interaction: discord.Interaction) -> None:
        embed = await self.cog.build_dashboard_embed(interaction, self.layout)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Personalizar", style=discord.ButtonStyle.secondary, emoji="🎛️")
    async def btn_customize(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = DashboardLayoutSelect(self.layout)

        async def _on_select(select_interaction: discord.Interaction):
            self.layout = list(select.values)
            await self.cog.save_dashboard_layout(select_interaction.user.id, self.layout)
            embed = await self.cog.build_dashboard_embed(select_interaction, self.layout)
            await select_interaction.response.edit_message(
                content="✅ Layout salvo. Volte ao dashboard e clique em **Atualizar** para aplicar.",
                embed=embed,
                view=None,
            )

        select.callback = _on_select
        view = discord.ui.View(timeout=120)
        view.add_item(select)
        await interaction.response.send_message(
            "🧭 Escolha as seções que deseja ver no dashboard:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Atualizar", style=discord.ButtonStyle.primary, emoji="🔄")
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)


class Experience(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.character_repo = CharacterRepository(bot.db)

    async def load_dashboard_layout(self, user_id: int) -> List[str]:
        async with self.bot.db.execute(
            "SELECT layout_json FROM user_dashboards WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return DASHBOARD_LAYOUT_DEFAULT
        try:
            layout = json.loads(row[0])
        except json.JSONDecodeError:
            return DASHBOARD_LAYOUT_DEFAULT
        return [section for section in layout if section in DASHBOARD_LAYOUT_OPTIONS]

    async def save_dashboard_layout(self, user_id: int, layout: Iterable[str]) -> None:
        payload = json.dumps(list(layout), ensure_ascii=False)
        await self.bot.db.execute(
            """
            INSERT INTO user_dashboards (user_id, layout_json, atualizado_em)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET layout_json = excluded.layout_json,
                atualizado_em = excluded.atualizado_em
            """,
            (user_id, payload),
        )
        await self.bot.db.commit()

    async def build_dashboard_embed(self, interaction: discord.Interaction, layout: Iterable[str]) -> discord.Embed:
        embed = themed_embed(f"{DEFAULT_THEME.tokens.emojis['dashboard']} Dashboard do Aventureiro", variant="brand")
        embed.set_footer(text="Navegação padronizada • Personalize suas seções")

        character_summary = await self.character_repo.fetch_character_summary_by_user(interaction.user.id)
        inventory_count = await self._count_inventory_items(interaction.user.id)
        quests_count = await self._count_active_quests(interaction.user.id)
        solo_status = await self._fetch_solo_status(interaction.user.id)
        combat_status = await self._fetch_combat_status(interaction.user.id)

        section_builders = {
            "resumo": lambda: build_section_lines(
                "Resumo",
                [
                    f"Personagem: **{character_summary[1]}**" if character_summary else "Personagem: —",
                    f"HP: {character_summary[2]}/{character_summary[3]}" if character_summary else "HP: —",
                ],
            ),
            "atalhos": lambda: build_section_lines(
                "Atalhos",
                ["`/ficha` • `/inventario` • `/rolar`", "`/quest_gerar` • `/combate_entrar`"],
            ),
            "inventario": lambda: build_section_lines(
                "Inventário",
                [f"Itens registrados: **{inventory_count}**"],
            ),
            "quests": lambda: build_section_lines(
                "Quests",
                [f"Ativas para você: **{quests_count}**"],
            ),
            "campanha": lambda: build_section_lines(
                "Campanha Solo",
                [solo_status or "Nenhuma campanha solo em andamento."],
            ),
            "combate": lambda: build_section_lines(
                "Combate",
                [combat_status or "Nenhuma batalha ativa no momento."],
            ),
        }

        for section in layout:
            builder = section_builders.get(section)
            if not builder:
                continue
            embed.add_field(name="\u200b", value=builder(), inline=False)
        return embed

    async def _count_inventory_items(self, user_id: int) -> int:
        async with self.bot.db.execute(
            "SELECT COUNT(*) FROM inventario WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def _count_active_quests(self, user_id: int) -> int:
        async with self.bot.db.execute(
            """
            SELECT COUNT(*)
            FROM quests q
            JOIN quest_participantes qp ON qp.quest_id = q.id
            WHERE qp.user_id = ? AND LOWER(q.status) != 'concluida'
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def _fetch_solo_status(self, user_id: int) -> str | None:
        async with self.bot.db.execute(
            """
            SELECT capitulo, progresso, gancho
            FROM solo_campaigns
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        capitulo, progresso, gancho = row
        gancho_text = f"Gancho: {gancho}" if gancho else "Gancho: —"
        return f"Capítulo {capitulo} • Progresso {progresso}% • {gancho_text}"

    async def _fetch_combat_status(self, user_id: int) -> str | None:
        if not await self._table_exists("combats") or not await self._table_exists("combat_players"):
            return None
        async with self.bot.db.execute(
            """
            SELECT c.status
            FROM combats c
            JOIN combat_players cp ON cp.combat_id = c.id
            WHERE cp.user_id = ?
            ORDER BY c.id DESC
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        return f"Última sala: {row[0] or 'Em andamento'}"

    async def _table_exists(self, table: str) -> bool:
        async with self.bot.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table,),
        ) as cursor:
            return await cursor.fetchone() is not None

    @app_commands.command(name="onboarding", description="Inicia um onboarding guiado do bot.")
    async def onboarding(self, interaction: discord.Interaction):
        view = OnboardingView(ONBOARDING_STEPS)
        await interaction.response.send_message(embed=view._build_embed(), view=view, ephemeral=True)

    @app_commands.command(name="dashboard", description="Abre seu dashboard customizável.")
    async def dashboard(self, interaction: discord.Interaction):
        layout = await self.load_dashboard_layout(interaction.user.id)
        embed = await self.build_dashboard_embed(interaction, layout)
        view = DashboardView(self, interaction.user.id, layout)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Experience(bot))
