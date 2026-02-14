import asyncio
import io
import time
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import ui

from config import settings
from data.repositories import (
    CharacterRepository,
    InventoryRepository,
    RollsRepository,
    SkillRepository,
    SoloRepository,
)
from ui.base_view import BaseRPGView
from ui.design_system import apply_navigation_state
from ui.views import ConfirmarExclusaoView
from utils import rolar_dados, rolar_pericia_explosiva, gerar_barra
from utils.i18n import (
    I18nContext,
    format_currency,
    format_datetime,
    get_interaction_context,
    resolve_locale,
    translate,
)
from utils.roll_templates import resolve_roll_template

try:
    from utils.dc_table import DEFAULT_DC_THRESHOLDS, classificar_resultado
except Exception:  # pragma: no cover - fallback for mocked utils module in tests
    DEFAULT_DC_THRESHOLDS = (10, 15, 20, 25)

    def classificar_resultado(total: int, dc: Optional[int]) -> str:
        return "Resultado"

# ==============================================================================
# 0. HELPERS (LAYOUT)
# ==============================================================================

DEFAULT_THUMBNAIL_URL = "https://placehold.co/256x256/png?text=Ficha"

def _format_dual_column(items, name_width=12, value_width=5, ctx: Optional[I18nContext] = None):
    if not items:
        return ctx.t("ui.common.none_registered") if ctx else "_Nenhum registrado._"

    lines = []
    for idx in range(0, len(items), 2):
        left_name, left_value = items[idx]
        left_value = "—" if left_value is None or left_value == "" else left_value
        left = f"{str(left_name)[:name_width]:<{name_width}} {str(left_value)[:value_width]:>{value_width}}"

        right = ""
        if idx + 1 < len(items):
            right_name, right_value = items[idx + 1]
            right_value = "—" if right_value is None or right_value == "" else right_value
            right = f"{str(right_name)[:name_width]:<{name_width}} {str(right_value)[:value_width]:>{value_width}}"

        line = f"{left}   {right}".rstrip()
        lines.append(line)

    return "```\n" + "\n".join(lines) + "\n```"


def _format_list(items, prefix="• ", ctx: Optional[I18nContext] = None):
    if not items:
        return ctx.t("ui.common.none_registered") if ctx else "_Nenhum registrado._"
    return "\n".join([f"{prefix}{item}" for item in items])


def _format_percentual(atual, maximo):
    if maximo <= 0:
        return "0%"
    pct = max(min(atual / maximo, 1), 0)
    return f"{int(round(pct * 100))}%"


def _format_receitas_conhecidas(receitas, ctx: Optional[I18nContext] = None):
    if not receitas:
        return ctx.t("ui.common.none_unlocked") if ctx else "_Nenhuma receita desbloqueada._"
    return "\n".join([f"• **{nome}** ({base})" for nome, base in receitas])


def _cor_por_hp(hp_atual, hp_max):
    if hp_max <= 0:
        return 0xED4245
    pct = max(min(hp_atual / hp_max, 1), 0)
    if pct > 0.7:
        return 0x57F287
    if pct > 0.3:
        return 0xFEE75C
    return 0xED4245


def _gerar_barra_encumbrance(encumbrance_atual: int, capacidade_maxima: int, segmentos: int = 10) -> str:
    if capacidade_maxima <= 0:
        return "⬛" * segmentos

    proporcao = encumbrance_atual / capacidade_maxima
    preenchidos = min(segmentos, max(0, round(proporcao * segmentos)))
    vazios = segmentos - preenchidos

    if proporcao >= 1.0:
        cor = "🟥"
    elif proporcao >= 0.8:
        cor = "🟧"
    elif proporcao >= 0.5:
        cor = "🟨"
    else:
        cor = "🟩"

    return f"{cor * preenchidos}{'⬛' * vazios}"


def _set_footer_timestamp(
    embed: discord.Embed,
    texto_base: str = "",
    ctx: Optional[I18nContext] = None,
) -> None:
    now = datetime.now(timezone.utc)
    localized = format_datetime(now, locale=ctx.locale if ctx else None, timezone=ctx.timezone if ctx else None)
    if texto_base:
        embed.set_footer(text=f"{texto_base} • {localized}")
    else:
        embed.set_footer(text=localized)


def _build_author_name(
    nome: Optional[str],
    classe: Optional[str],
    raca: Optional[str],
    genero: Optional[str],
    ctx: Optional[I18nContext] = None,
) -> str:
    identity_bits = [item for item in (classe, raca, genero) if item]
    if nome and identity_bits:
        return f"{nome} • {' / '.join(identity_bits)}"
    if nome:
        return nome
    if identity_bits:
        return " • ".join(identity_bits)
    return ctx.t("ui.common.character_sheet") if ctx else "Ficha de Personagem"


def _apply_embed_identity(
    embed: discord.Embed,
    nome: Optional[str],
    classe: Optional[str],
    raca: Optional[str],
    genero: Optional[str],
    imagem_url: Optional[str],
    ctx: Optional[I18nContext] = None,
) -> None:
    author_name = _build_author_name(nome, classe, raca, genero, ctx)
    embed.set_author(name=f"📜 {author_name}")
    thumbnail_url = imagem_url or settings.default_character_thumbnail_url
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)


def _apply_embed_metadata(
    embed: discord.Embed,
    titulo: Optional[str],
    imagem_url: Optional[str],
    footer_text: str,
    ctx: Optional[I18nContext] = None,
) -> None:
    embed.set_author(name=titulo or (ctx.t("ui.common.no_title") if ctx else "Sem título"))
    thumbnail_url = imagem_url or DEFAULT_THUMBNAIL_URL
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    _set_footer_timestamp(embed, footer_text, ctx=ctx)


def _split_text(texto: str, limite: int = 3900) -> list[str]:
    texto = (texto or "").strip()
    if not texto:
        return [""]
    return [texto[i : i + limite] for i in range(0, len(texto), limite)]


def _resumir_texto(texto: str, limite: int = 180) -> str:
    texto = (texto or "").strip()
    if len(texto) <= limite:
        return texto
    return f"{texto[:limite]}..."


def _criar_embed_erro_formula(input_str: str) -> discord.Embed:
    """Gera um Embed de erro amigável para fórmulas de dados inválidas."""
    input_clean = input_str.strip()

    embed = discord.Embed(
        title="❌ Fórmula Inválida",
        description=f"Não entendi a fórmula `{input_clean}`.",
        color=0xED4245
    )

    # Tentativa de correção (Sugestão inteligente)
    import re
    # Se começou com 'd' seguido de número (ex: d20), esqueceu a quantidade
    if re.match(r"^d\d+", input_clean, re.IGNORECASE):
        sugestao = f"1{input_clean}"
        embed.description = f"Você quis dizer `{sugestao}`?"
        embed.add_field(name="💡 Dica", value=f"Sempre indique a quantidade de dados (ex: **1**d20).")

    # Se digitou apenas texto (ex: 'Fogo')
    elif re.match(r"^[a-zA-Z\s]+$", input_clean):
        embed.add_field(name="💡 Dica", value="Use notação de dados padrão (ex: 4d6). O nome da habilidade vai em outro campo!")

    embed.add_field(
        name="✅ Formatos Válidos",
        value="• `1d20` (Um dado de 20 faces)\n• `2d6+3` (Dois dados de 6 faces mais 3)\n• `10` (Valor fixo)",
        inline=False
    )

    return embed


async def _table_exists(db, table: str) -> bool:
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ) as cursor:
        return await cursor.fetchone() is not None


async def construir_embed_ficha(db, personagem_id, user_id, locale: str | None = None):
    ctx = I18nContext(
        locale=resolve_locale(locale),
        timezone=settings.default_timezone,
        currency=settings.default_currency,
    )
    character_repo = CharacterRepository(db)
    inventory_repo = InventoryRepository(db)
    skill_repo = SkillRepository(db)

    dados, atributos, pericias, itens = await asyncio.gather(
        character_repo.fetch_embed_details(personagem_id),
        character_repo.list_attributes(personagem_id, limit=12),
        skill_repo.list_skills_for_sheet(personagem_id, limit=10, order_by_name=True),
        inventory_repo.list_recent_items(user_id, limit=8),
    )

    if not dados:
        return None

    (
        nome, titulo, raca, classe, genero, nivel, historia, img, ouro, hp_atual, hp_max, mp_max,
        ataque, defesa, xp_atual, vigor_atual, vigor_max, toxicidade_atual, toxicidade_max, local
    ) = dados
    if hp_atual is None:
        hp_atual = hp_max
    if vigor_atual is None:
        vigor_atual = vigor_max
    if toxicidade_atual is None:
        toxicidade_atual = 0
    atributos_map = {nome: valor for nome, valor in atributos}
    derived_stats = character_repo.calculate_derived_stats(atributos_map)

    pericias_formatadas = [(p[0], p[1] or "—") for p in pericias]
    itens_formatados = [
        f"**{nome_item}** ({tipo})" if tipo else f"**{nome_item}**"
        for nome_item, tipo in itens
    ]

    embed = discord.Embed(title=f"📜 {nome}", color=_cor_por_hp(hp_atual, hp_max))
    _apply_embed_identity(embed, nome, classe, raca, genero, img, ctx)
    identidade_partes = []
    if classe:
        identidade_partes.append(f"*{classe}*")
    if raca:
        identidade_partes.append(f"**{raca}**")
    if genero:
        identidade_partes.append(genero)
    identidade_texto = " • ".join(identidade_partes) if identidade_partes else ctx.t("ui.common.no_record")
    embed.add_field(
        name=ctx.t("ui.sheet.identity"),
        value=f"{identidade_texto} • Nível **{nivel}**",
        inline=False,
    )
    embed.add_field(
        name=ctx.t("ui.sheet.history"),
        value=historia or ctx.t("ui.common.no_record"),
        inline=False,
    )
    embed.add_field(name=ctx.t("ui.sheet.location"), value=local or ctx.t("ui.common.unknown"), inline=True)
    embed.add_field(name=ctx.t("ui.sheet.gold"), value=ctx.format_currency(ouro or 0), inline=True)
    embed.add_field(name=ctx.t("ui.sheet.xp"), value=str(xp_atual), inline=True)

    hp_pct = _format_percentual(hp_atual, hp_max)
    vigor_pct = _format_percentual(vigor_atual, vigor_max)

    # UX: Add dynamic status bars (5 segments for inline fit)
    hp_bar = gerar_barra(hp_atual, hp_max, 5)
    vigor_bar = gerar_barra(vigor_atual, vigor_max, 5)

    recursos = (
        f"❤️ {hp_bar} {hp_atual}/{hp_max}\n"
        f"⚡ {vigor_bar} {vigor_atual}/{vigor_max}\n"
        f"✨ MP {mp_max}\n"
        f"☠️ Toxicidade {toxicidade_atual}/{toxicidade_max}"
    )
    embed.add_field(name=ctx.t("ui.sheet.resources"), value=recursos, inline=True)
    embed.add_field(
        name=ctx.t("ui.sheet.combat_magic"),
        value=(
            f"{ctx.t('ui.sheet.attack')} **{ataque}**"
            f" • {ctx.t('ui.sheet.current_sp')} **{defesa}**"
            f" • MP **{mp_max}**"
        ),
        inline=True
    )
    embed.add_field(
        name=ctx.t("ui.sheet.attributes"),
        value=_format_dual_column(atributos, name_width=10, value_width=3, ctx=ctx),
        inline=True
    )
    derived_items = [
        ("Stun", derived_stats["Stun"]),
        ("Run", derived_stats["Run"]),
        ("Leap", derived_stats["Leap"]),
        ("HP", derived_stats["HP"]),
        ("Stamina", derived_stats["Stamina"]),
        ("Vigor", derived_stats["Vigor"]),
        ("Recovery", derived_stats["Recovery"]),
    ]
    embed.add_field(
        name=ctx.t("ui.sheet.derived"),
        value=_format_dual_column(derived_items, name_width=9, value_width=5, ctx=ctx),
        inline=True
    )
    embed.add_field(
        name=ctx.t("ui.sheet.skills_signs"),
        value=_format_dual_column(pericias_formatadas, name_width=12, value_width=6, ctx=ctx),
        inline=True
    )
    embed.add_field(
        name=ctx.t("ui.sheet.highlight_items"),
        value=_format_list(itens_formatados, ctx=ctx),
        inline=False
    )

    _set_footer_timestamp(embed, ctx.t("ui.sheet.scroll_footer"), ctx=ctx)
    return embed

# ==============================================================================
# 1. MODAIS (CRIAR E EDITAR)
# ==============================================================================

class NovaHabilidadeModal(ui.Modal):
    def __init__(self, personagem_id, view_pai, locale: str | None = None):
        locale = resolve_locale(locale)
        super().__init__(title=translate("ui.sheet.new_skill_title", locale=locale))
        self.personagem_id = personagem_id
        self.view_pai = view_pai
        self.locale = locale

        self.nome = ui.TextInput(
            label=translate("ui.sheet.skill_name_label", locale=locale),
            placeholder=translate("ui.sheet.skill_name_placeholder", locale=locale),
        )
        self.dado = ui.TextInput(
            label=translate("ui.sheet.skill_damage_label", locale=locale),
            placeholder=translate("ui.sheet.skill_damage_placeholder", locale=locale),
            required=False,
        )
        self.descricao = ui.TextInput(
            label=translate("ui.sheet.skill_desc_label", locale=locale),
            style=discord.TextStyle.paragraph,
            required=False,
            placeholder=translate("ui.sheet.skill_desc_placeholder", locale=locale),
        )

        self.add_item(self.nome)
        self.add_item(self.dado)
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        if self.dado.value:
            detalhes, _ = rolar_dados(self.dado.value)
            if detalhes is None:
                embed = discord.Embed(
                    title="❌ Fórmula Inválida",
                    description=f"Não consegui entender a fórmula **`{self.dado.value}`**.",
                    color=0xED4245
                )
                embed.add_field(
                    name="💡 Exemplos de Fórmulas",
                    value="• `1d20+5` (Um d20 mais 5)\n• `2d6` (Dois d6)\n• `d10` (Um d10)\n• `10` (Valor fixo)",
                    inline=False
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        skill_repo = SkillRepository(interaction.client.db)
        await skill_repo.add_skill(self.personagem_id, self.nome.value, self.descricao.value, self.dado.value)
        
        # Rich Success State
        embed = discord.Embed(
            title="✨ Habilidade Aprendida!",
            color=0x57F287
        )
        embed.add_field(name="Nome", value=self.nome.value, inline=True)
        if self.dado.value:
            embed.add_field(name="Dano/Efeito", value=self.dado.value, inline=True)
        if self.descricao.value:
            embed.add_field(name="Descrição", value=self.descricao.value, inline=False)
        embed.set_footer(text="Habilidade adicionada à sua ficha.")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

class EditarHabilidadeModal(ui.Modal):
    def __init__(self, skill_id, current_nome, current_dado, current_desc, view_pai, locale: str | None = None):
        locale = resolve_locale(locale)
        super().__init__(title=translate("ui.sheet.edit_skill_title", locale=locale))
        self.skill_id = skill_id
        self.view_pai = view_pai

        self.nome_input = ui.TextInput(
            label=translate("ui.sheet.skill_name_label", locale=locale),
            default=current_nome,
        )
        self.dado_input = ui.TextInput(
            label=translate("ui.sheet.skill_damage_label", locale=locale),
            default=current_dado,
            required=False,
        )
        self.desc_input = ui.TextInput(
            label=translate("ui.sheet.skill_desc_label", locale=locale),
            default=current_desc,
            style=discord.TextStyle.paragraph,
            required=False,
        )

        self.add_item(self.nome_input)
        self.add_item(self.dado_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        if self.dado_input.value:
            detalhes, _ = rolar_dados(self.dado_input.value)
            if detalhes is None:
                embed = discord.Embed(
                    title="❌ Fórmula Inválida",
                    description=f"Não consegui entender a fórmula **`{self.dado_input.value}`**.",
                    color=0xED4245
                )
                embed.add_field(
                    name="💡 Exemplos de Fórmulas",
                    value="• `1d20+5` (Um d20 mais 5)\n• `2d6` (Dois d6)\n• `d10` (Um d10)\n• `10` (Valor fixo)",
                    inline=False
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        skill_repo = SkillRepository(interaction.client.db)
        await skill_repo.update_skill(self.skill_id, self.nome_input.value, self.dado_input.value, self.desc_input.value)
        
        # Rich Success State
        embed = discord.Embed(
            title="✏️ Habilidade Atualizada!",
            color=0xFEE75C
        )
        embed.add_field(name="Nome", value=self.nome_input.value, inline=True)
        if self.dado_input.value:
            embed.add_field(name="Dano/Efeito", value=self.dado_input.value, inline=True)
        if self.desc_input.value:
            embed.add_field(name="Descrição", value=self.desc_input.value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

class RolarPericiaModal(ui.Modal):
    def __init__(self, atributo_nome: str, atributo_valor: int, locale: str | None = None):
        locale = resolve_locale(locale)
        super().__init__(title=translate("ui.sheet.roll_skill_title", locale=locale))
        self.atributo_nome = atributo_nome
        self.atributo_valor = atributo_valor
        self.locale = locale
        self.dcs = {
            "Fácil": 10,
            "Média": 15,
            "Difícil": 20,
            "Extrema": 25,
        }

        self.pericia_nome = ui.TextInput(
            label=translate("ui.sheet.skill_optional_label", locale=locale),
            required=False,
            placeholder=translate("ui.sheet.skill_optional_placeholder", locale=locale),
        )
        self.pericia_valor = ui.TextInput(
            label=translate("ui.sheet.skill_value_label", locale=locale),
            placeholder=translate("ui.sheet.skill_value_placeholder", locale=locale),
            required=False,
        )
        self.dificuldade_input = ui.TextInput(
            label=translate("ui.sheet.difficulty_label", locale=locale),
            required=False,
            placeholder=translate("ui.sheet.difficulty_placeholder", locale=locale),
        )

        self.add_item(self.pericia_nome)
        self.add_item(self.pericia_valor)
        self.add_item(self.dificuldade_input)

    def _t(self, key: str, **kwargs) -> str:
        return translate(key, locale=self.locale, **kwargs)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        try:
            val_str = self.pericia_valor.value
            pericia_valor = int(val_str) if val_str else 0
        except ValueError:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.invalid_skill_value"),
                ephemeral=True,
            )

        dc_informada = self._parse_dificuldade()

        rolagens, total, direcao = rolar_pericia_explosiva(self.atributo_valor, pericia_valor)
        classificacao = classificar_resultado(total, dc_informada)

        etiqueta = self.pericia_nome.value.strip() if self.pericia_nome.value else ctx.t("ui.sheet.skill_label_default")
        detalhes_rolagem = ", ".join(map(str, rolagens))
        explosao_txt = ""
        if direcao == 1:
            explosao_txt = ctx.t("ui.sheet.explosion_up")
        elif direcao == -1:
            explosao_txt = ctx.t("ui.sheet.explosion_down")

        embed = discord.Embed(
            title=f"🎯 {etiqueta} - {self.atributo_nome}",
            color=0x2b2d31
        )
        embed.add_field(
            name=ctx.t("ui.sheet.roll_field"),
            value=f"[{detalhes_rolagem}]{explosao_txt}",
            inline=False
        )
        embed.add_field(
            name=ctx.t("ui.sheet.formula"),
            value=f"1d10 + Stat({self.atributo_valor}) + Skill({pericia_valor})",
            inline=False
        )
        if dc_informada is not None:
            embed.add_field(name="DC", value=str(dc_informada), inline=True)
        else:
            tabela_txt = "/".join(map(str, DEFAULT_DC_THRESHOLDS))
            embed.add_field(name=ctx.t("ui.sheet.difficulty_table"), value=tabela_txt, inline=True)
        embed.add_field(name=ctx.t("ui.sheet.total"), value=f"# **{total}**", inline=False)
        resultado = self._avaliar_dificuldade(total)
        if resultado:
            embed.add_field(
                name=ctx.t("ui.sheet.result_vs_dc", dc=resultado["dc"], label=resultado["rotulo"]),
                value=f"{resultado['texto']} ({ctx.t('ui.sheet.margin')} {resultado['margem']:+})",
                inline=False,
            )
        dcs_texto = "\n".join([f"• **{nome}**: {valor}" for nome, valor in self.dcs.items()])
        embed.add_field(name=ctx.t("ui.sheet.reference_dcs"), value=dcs_texto, inline=False)

        if dc_informada is not None:
            margem = total - dc_informada
            if margem < 0:
                nivel = ctx.t("ui.sheet.failure")
            elif margem == 0:
                nivel = ctx.t("ui.sheet.marginal_success")
            elif margem < 10:
                nivel = ctx.t("ui.sheet.success")
            else:
                nivel = ctx.t("ui.sheet.critical")
            embed.add_field(
                name=ctx.t("ui.sheet.dc_comparison"),
                value=f"DC **{dc_informada}** ({ctx.t('ui.sheet.difference')}: {margem:+d})",
                inline=False
            )
        else:
            if total >= self.dcs["Extrema"]:
                nivel = ctx.t("ui.sheet.critical")
            elif total >= self.dcs["Difícil"]:
                nivel = ctx.t("ui.sheet.major_success")
            elif total >= self.dcs["Média"]:
                nivel = ctx.t("ui.sheet.success")
            elif total >= self.dcs["Fácil"]:
                nivel = ctx.t("ui.sheet.marginal_success")
            else:
                nivel = ctx.t("ui.sheet.failure")

        embed.add_field(name=ctx.t("ui.sheet.level"), value=nivel, inline=False)
        embed.add_field(name=ctx.t("ui.sheet.classification"), value=classificacao, inline=False)

        # Palette: UX Improvement - Color coded results
        color_map = {
            "Falha": 0xED4245,           # Red
            "Vitória Marginal": 0xFEE75C,# Yellow
            "Vitória": 0x57F287,         # Green
            "Vitória Maior": 0x57F287,   # Green
            "Crítica": 0xFFD700,         # Gold
            "Sucesso": 0x57F287,         # Green (via _avaliar_dificuldade fallback)
        }
        embed.color = color_map.get(nivel, 0x2b2d31)

        await interaction.response.send_message(embed=embed)

    def _parse_dificuldade(self) -> Optional[int]:
        dificuldade_raw = self.dificuldade_input.value.strip() if self.dificuldade_input.value else ""
        if not dificuldade_raw:
            return None

        tabela_dificuldade = {
            "facil": 10,
            "fácil": 10,
            "medio": 15,
            "médio": 15,
            "dificil": 20,
            "difícil": 20,
            "epico": 25,
            "épico": 25,
            "easy": 10,
            "medium": 15,
            "hard": 20,
            "extreme": 25,
        }
        dificuldade_normalizada = dificuldade_raw.lower()
        dc = tabela_dificuldade.get(dificuldade_normalizada)
        if dc is not None:
            return dc
        try:
            return int(dificuldade_raw)
        except ValueError:
            return None

    def _avaliar_dificuldade(self, total: int):
        dificuldade_raw = self.dificuldade_input.value.strip() if self.dificuldade_input.value else ""
        if not dificuldade_raw:
            return None

        tabela_dificuldade = {
            "facil": 10,
            "fácil": 10,
            "medio": 15,
            "médio": 15,
            "dificil": 20,
            "difícil": 20,
            "epico": 25,
            "épico": 25,
            "easy": 10,
            "medium": 15,
            "hard": 20,
            "extreme": 25,
        }
        dificuldade_normalizada = dificuldade_raw.lower()
        dc = tabela_dificuldade.get(dificuldade_normalizada)
        rotulo = dificuldade_raw.title()
        if dc is None:
            try:
                dc = int(dificuldade_raw)
                rotulo = self._t("ui.sheet.custom")
            except ValueError:
                return None

        margem = total - dc
        if margem < 0:
            texto = self._t("ui.sheet.failure")
        elif margem < 5:
            texto = self._t("ui.sheet.marginal_success")
        elif margem < 10:
            texto = self._t("ui.sheet.success")
        else:
            texto = self._t("ui.sheet.critical")

        if dc in tabela_dificuldade.values():
            rotulo = {
                10: self._t("ui.sheet.easy"),
                15: self._t("ui.sheet.medium"),
                20: self._t("ui.sheet.hard"),
                25: self._t("ui.sheet.extreme"),
            }.get(dc, rotulo)

        return {
            "dc": dc,
            "margem": margem,
            "texto": texto,
            "rotulo": rotulo,
        }

class BuscarPericiaModal(ui.Modal):
    def __init__(self, personagem_id, locale: str | None = None):
        locale = resolve_locale(locale)
        super().__init__(title=translate("ui.sheet.search_skill_title", locale=locale))
        self.personagem_id = personagem_id
        self.locale = locale

        self.termo = ui.TextInput(
            label=translate("ui.sheet.search_skill_label", locale=locale),
            placeholder=translate("ui.sheet.search_skill_placeholder", locale=locale),
            required=True,
        )
        self.add_item(self.termo)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        termo_busca = self.termo.value.strip()
        termo_sql = f"%{termo_busca}%"
        skill_repo = SkillRepository(interaction.client.db)
        resultados = await skill_repo.search_skills(self.personagem_id, termo_sql, limit=5)

        # Palette: Add "New Search" view to allow immediate retry
        view_retry = NovaBuscaView(self.personagem_id)

        if not resultados:
            embed = discord.Embed(
                title=ctx.t("ui.sheet.no_skills_found_title"),
                description=ctx.t("ui.sheet.no_skills_found_desc", term=termo_busca),
                color=0xED4245
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True, view=view_retry)

        embed = discord.Embed(
            title=ctx.t("ui.sheet.search_results_title", term=self.termo.value),
            color=0x5865F2  # Blurple
        )

        for nome, dado, descricao in resultados:
            dado_txt = f" `{dado}`" if dado else ""
            resumo = (descricao[:100] + "...") if descricao and len(descricao) > 100 else (descricao or ctx.t("ui.common.no_description"))
            embed.add_field(
                name=f"{nome}{dado_txt}",
                value=resumo,
                inline=False
            )

        embed.set_footer(text="Mostrando os 5 primeiros resultados.")
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view_retry)

class TentarBuscaNovamenteView(ui.View):
    def __init__(self, personagem_id):
        super().__init__(timeout=60)
        self.personagem_id = personagem_id

    @ui.button(label="🔎 Tentar Novamente", style=discord.ButtonStyle.primary)
    async def btn_retry(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BuscarPericiaModal(self.personagem_id))

# ==============================================================================
# 2. VIEWS AUXILIARES (GERENCIAMENTO)
# ==============================================================================

class NovaBuscaView(ui.View):
    def __init__(self, personagem_id):
        super().__init__(timeout=60)
        self.personagem_id = personagem_id

    @ui.button(label="Nova Busca", emoji="🔎", style=discord.ButtonStyle.primary)
    async def btn_nova_busca(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BuscarPericiaModal(self.personagem_id))

class AcoesHabilidadeView(ui.View):
    def __init__(self, skill_id, nome, dado, desc, view_ficha, locale: str | None = None):
        super().__init__(timeout=60)
        self.skill_id = skill_id
        self.nome = nome
        self.dado = dado
        self.desc = desc
        self.view_ficha = view_ficha
        self.locale = resolve_locale(locale)
        self._apply_labels()

    def _apply_labels(self) -> None:
        for child in self.children:
            if not isinstance(child, ui.Button):
                continue
            # Handle both direct function and _ViewCallback wrapper
            callback = child.callback
            if hasattr(callback, "callback"):  # _ViewCallback wrapper
                callback = callback.callback

            if callback.__name__ == "btn_editar":
                child.label = translate("ui.sheet.edit_label", locale=self.locale)
            elif callback.__name__ == "btn_excluir":
                child.label = translate("ui.sheet.delete_label", locale=self.locale)

    @ui.button(label="Editar", emoji="✏️", style=discord.ButtonStyle.primary)
    async def btn_editar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            EditarHabilidadeModal(
                self.skill_id,
                self.nome,
                self.dado,
                self.desc,
                self.view_ficha,
                locale=self.locale,
            )
        )

    @ui.button(label="Excluir", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def btn_excluir(self, interaction: discord.Interaction, button: ui.Button):
        async def confirmar(itx: discord.Interaction):
            skill_repo = SkillRepository(itx.client.db)
            await skill_repo.delete_skill(self.skill_id)

            # Rich Success State
            embed = discord.Embed(
                title="🗑️ Habilidade Removida",
                description=f"A habilidade **{self.nome}** foi excluída da sua ficha.",
                color=0xED4245
            )
            await itx.response.edit_message(content=None, embed=embed, view=None)
            await self.view_ficha.atualizar_botoes_habilidade(itx)

        async def cancelar(itx: discord.Interaction):
            # UX Improvement: Restore the previous view so user doesn't lose context
            view_restored = AcoesHabilidadeView(
                self.skill_id,
                self.nome,
                self.dado,
                self.desc,
                self.view_ficha,
                locale=self.locale,
            )
            await itx.response.edit_message(
                content=translate("ui.sheet.manage_skill_title", locale=self.locale, name=self.nome),
                view=view_restored
            )

        view_conf = ConfirmarExclusaoView(confirmar, cancelar, locale=self.locale)
        await interaction.response.edit_message(
            content=translate("ui.sheet.confirm_delete_skill", locale=self.locale, name=self.nome),
            view=view_conf
        )
        # Não chamamos self.stop() aqui porque queremos que esta view continue ativa
        # caso o usuário cancele (embora neste caso a view seja substituída na mensagem)
        # Como substituímos a mensagem, esta view (AcoesHabilidadeView) não receberá mais eventos daquela mensagem específica.
        self.stop()

class SelecionarHabilidadeSelect(ui.Select):
    def __init__(self, skills, view_ficha, locale: str | None = None):
        self.skills_map = {str(s[0]): s for s in skills}
        self.locale = resolve_locale(locale)
        
        options = []
        for id_skill, nome, dado, desc in skills:
            desc_curta = f"({dado}) " if dado else ""
            desc_curta += desc[:50] if desc else translate("ui.common.no_description", locale=self.locale)
            
            # UX Improvement: Use consistent emojis for skill types
            emoji = "🎲" if dado else "✨"

            options.append(discord.SelectOption(
                label=nome[:100], 
                value=str(id_skill), 
                description=desc_curta[:100],
                emoji=emoji
            ))

        super().__init__(
            placeholder=translate("ui.sheet.select_skill_placeholder", locale=self.locale),
            min_values=1,
            max_values=1,
            options=options,
        )
        self.view_ficha = view_ficha

    async def callback(self, interaction: discord.Interaction):
        skill_id = self.values[0]
        data = self.skills_map.get(skill_id)
        if not data:
            return await interaction.response.send_message(
                translate("ui.sheet.skill_not_found", locale=self.locale),
                ephemeral=True,
            )
            
        id_skill, nome, dado, desc = data
        
        view = AcoesHabilidadeView(id_skill, nome, dado, desc, self.view_ficha, locale=self.locale)
        await interaction.response.send_message(
            translate("ui.sheet.manage_skill_title", locale=self.locale, name=nome),
            view=view, 
            ephemeral=True
        )

class GerenciarHabilidadesView(ui.View):
    def __init__(self, skills, view_ficha, locale: str | None = None):
        super().__init__(timeout=60)
        self.add_item(SelecionarHabilidadeSelect(skills, view_ficha, locale=locale))

class FerimentosCriticosSelect(ui.Select):
    def __init__(self, locale: str | None = None):
        ferimentos = [
            ("Fratura", "Movimento reduzido e penalidade em testes físicos."),
            ("Sangramento", "Perde HP por turno até estancar."),
            ("Concussão", "Penalidade em Percepção e Magia."),
            ("Perfuração", "Ações de combate com desvantagem."),
            ("Queimadura", "Resistência reduzida e dor contínua.")
        ]
        self.locale = resolve_locale(locale)

        options = [
            discord.SelectOption(
                label=nome,
                value=nome,
                description=desc[:100],
                emoji="🩸"
            ) for nome, desc in ferimentos
        ]
        super().__init__(
            placeholder=translate("ui.sheet.ferimentos_placeholder", locale=self.locale),
            min_values=1,
            max_values=1,
            options=options,
        )
        self.ferimentos_map = {nome: desc for nome, desc in ferimentos}
        self.row = 3

    async def callback(self, interaction: discord.Interaction):
        ferimento = self.values[0]
        desc = self.ferimentos_map.get(
            ferimento,
            translate("ui.sheet.ferimentos_no_details", locale=self.locale),
        )
        embed = discord.Embed(
            title=translate("ui.sheet.ferimentos_title", locale=self.locale, name=ferimento),
            description=desc,
            color=0x8B1A1A,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class FerimentosCriticosView(ui.View):
    def __init__(self, locale: str | None = None):
        super().__init__(timeout=120)
        self.add_item(FerimentosCriticosSelect(locale=locale))

class PocaoSelect(ui.Select):
    def __init__(self, potions, personagem_id, locale: str | None = None):
        self.personagem_id = personagem_id
        self.potion_map = {str(p[0]): p for p in potions}
        self.locale = resolve_locale(locale)
        options = [
            discord.SelectOption(
                label=nome[:100],
                value=str(item_id),
                description=(efeito or translate("ui.common.no_effect", locale=self.locale))[:100],
                emoji="🧪"
            )
            for item_id, nome, efeito in potions
        ]
        super().__init__(
            placeholder=translate("ui.sheet.potion_placeholder", locale=self.locale),
            min_values=1,
            max_values=1,
            options=options,
        )
        self.row = 3

    async def callback(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        item_id = self.values[0]
        potion = self.potion_map.get(item_id)
        if not potion:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.potion_not_found"),
                ephemeral=True,
            )

        _, nome, efeito = potion
        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)
        row = await character_repo.fetch_toxicity(self.personagem_id)

        if not row:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        toxicidade_atual, toxicidade_max = row
        custo_toxicidade = 10
        nova_toxicidade = min((toxicidade_atual or 0) + custo_toxicidade, toxicidade_max or 100)

        await character_repo.update_toxicity(self.personagem_id, nova_toxicidade)
        await inventory_repo.delete_item(item_id)

        embed = discord.Embed(
            title=ctx.t("ui.sheet.potion_consumed_title", name=interaction.user.display_name, potion=nome),
            description=efeito or ctx.t("ui.sheet.potion_effect_default"),
            color=0x4B7B6F,
        )

        pct = nova_toxicidade / toxicidade_max if toxicidade_max > 0 else 0
        if pct <= 0.3:
            cor = "🟩"
        elif pct <= 0.6:
            cor = "🟨"
        else:
            cor = "🟥"
        tox_bar = gerar_barra(nova_toxicidade, toxicidade_max, tamanho=5, cor_cheio=cor)

        embed.add_field(
            name=ctx.t("ui.sheet.toxicity"),
            value=f"{tox_bar} +{custo_toxicidade} ({nova_toxicidade}/{toxicidade_max})",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.view:
            await self.view.atualizar_botoes_habilidade(interaction, target_message=interaction.message)

class PocaoView(ui.View):
    def __init__(self, potions, personagem_id, locale: str | None = None):
        super().__init__(timeout=120)
        self.add_item(PocaoSelect(potions, personagem_id, locale=locale))

# ==============================================================================
# 3. COMPONENTES DA FICHA PRINCIPAL
# ==============================================================================

class HabilidadeButton(ui.Button):
    def __init__(self, nome, dado, descricao, personagem_id=None, vigor_cost=0, locale: str | None = None):
        if dado:
            emoji = "🎲"
            style = discord.ButtonStyle.primary
            label_btn = f"{nome} [{dado}]"
        else:
            emoji = "✨"
            style = discord.ButtonStyle.secondary
            label_btn = nome

        super().__init__(style=style, label=label_btn, emoji=emoji, row=None)
        self.nome_habilidade = nome
        self.dado_habilidade = dado
        self.desc_habilidade = descricao
        self.personagem_id = personagem_id
        self.vigor_cost = vigor_cost
        self.locale = resolve_locale(locale)

    async def callback(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        vigor_feedback = None
        if self.personagem_id and self.vigor_cost:
            character_repo = CharacterRepository(interaction.client.db)
            row = await character_repo.fetch_vigor(self.personagem_id)

            if not row:
                return await interaction.response.send_message(
                    ctx.t("ui.sheet.character_not_found"),
                    ephemeral=True,
                )

            vigor_atual, vigor_max = row
            if vigor_atual is None:
                vigor_atual = vigor_max

            if vigor_atual < self.vigor_cost:
                vigor_bar = gerar_barra(vigor_atual, vigor_max, tamanho=5)
                embed_erro = discord.Embed(
                    title="⚠️ Vigor Insuficiente",
                    description=f"Você precisa de **{self.vigor_cost}** Vigor para usar **{self.nome_habilidade}**, mas tem apenas **{vigor_atual}**.",
                    color=0xED4245
                )
                embed_erro.add_field(name="Vigor Atual", value=f"{vigor_bar} {vigor_atual}/{vigor_max}", inline=False)
                return await interaction.response.send_message(embed=embed_erro, ephemeral=True)

            novo_vigor = max(vigor_atual - self.vigor_cost, 0)
            await character_repo.update_vigor(self.personagem_id, novo_vigor)

            # Palette: Add visual feedback for Vigor cost
            bar = gerar_barra(novo_vigor, vigor_max, tamanho=5)
            vigor_feedback = f"{ctx.t('ui.sheet.vigor')}: {bar} {novo_vigor}/{vigor_max}"

        embed = discord.Embed(
            title=ctx.t("ui.sheet.use_skill_title", name=interaction.user.display_name, skill=self.nome_habilidade),
            color=0xFF5500,
        )
        embed.description = self.desc_habilidade or "..."

        if vigor_feedback:
            embed.set_footer(text=vigor_feedback)
        
        if self.dado_habilidade:
            detalhes, total = rolar_dados(self.dado_habilidade)
            if detalhes:
                embed.add_field(
                    name=ctx.t("ui.sheet.roll_field_title"),
                    value=f"`{self.dado_habilidade}`\n{ctx.t('ui.sheet.result')}: {detalhes}\n# **{total}**",
                )
        
        await interaction.response.send_message(embed=embed)
        if self.view:
            await self.view.atualizar_botoes_habilidade(interaction, target_message=interaction.message)

class AtributoButton(ui.Button):
    def __init__(self, nome, valor, locale: str | None = None):
        label_btn = f"{nome} ({valor})"
        super().__init__(style=discord.ButtonStyle.secondary, label=label_btn, emoji="🎯", row=None)
        self.nome_atributo = nome
        self.valor_atributo = valor
        self.locale = resolve_locale(locale)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            RolarPericiaModal(self.nome_atributo, self.valor_atributo, locale=self.locale)
        )


class RolagemCombateButton(ui.Button):
    def __init__(self, label, emoji, personagem_id, formula_template, locale: str | None = None):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, row=2)
        self.personagem_id = personagem_id
        self.formula_template = formula_template
        self.locale = resolve_locale(locale)

    async def callback(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        character_repo = CharacterRepository(interaction.client.db)
        ataque = await character_repo.fetch_attack(self.personagem_id)

        if ataque is None:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        ataque = ataque or 0
        formula = self.formula_template.format(ataque=ataque)
        detalhes, total = rolar_dados(formula)
        if detalhes is None:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.invalid_formula"),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=ctx.t("ui.sheet.roll_result_title", name=interaction.user.display_name, label=self.label),
            description=f"`{formula}`\n{ctx.t('ui.sheet.result')}: {detalhes}\n**{ctx.t('ui.sheet.total')}: {total}**",
            color=0xB5651D,
        )
        await interaction.response.send_message(embed=embed)


class RolagemPadraoButton(ui.Button):
    def __init__(self, label: str, emoji: str, personagem_id: int, formula_template: str, locale: str | None = None):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, row=2)
        self.personagem_id = personagem_id
        self.formula_template = formula_template
        self.locale = resolve_locale(locale)

    async def callback(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        character_repo = CharacterRepository(interaction.client.db)
        atributos = await character_repo.list_attributes_dict(self.personagem_id)
        formula_resolvida, missing = resolve_roll_template(self.formula_template, atributos)

        if missing:
            faltantes = ", ".join(sorted(set(missing)))
            return await interaction.response.send_message(
                ctx.t("ui.sheet.attributes_missing", missing=faltantes),
                ephemeral=True,
            )

        detalhes, total = rolar_dados(formula_resolvida)
        if detalhes is None:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.invalid_formula"),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=ctx.t("ui.sheet.roll_result_title", name=interaction.user.display_name, label=self.label),
            description=f"`{formula_resolvida}`\n{ctx.t('ui.sheet.result')}: {detalhes}\n**{ctx.t('ui.sheet.total')}: {total}**",
            color=0x3D5A80,
        )
        await interaction.response.send_message(embed=embed)


class ExplorarConhecimentoButton(ui.Button):
    def __init__(self, personagem_id: int, locale: str | None = None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=translate("ui.sheet.explore_knowledge", locale=resolve_locale(locale)),
            emoji="📚",
            row=2,
        )
        self.personagem_id = personagem_id
        self.locale = resolve_locale(locale)

    async def callback(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        db = interaction.client.db
        required_tables = ("lore_entry_tags", "lore_tags", "lore_entries")
        for table in required_tables:
            if not await _table_exists(db, table):
                return await interaction.response.send_message(
                    ctx.t("ui.sheet.lore_tags_unavailable"),
                    ephemeral=True,
                )

        if not await _table_exists(db, "personagem_tags"):
            return await interaction.response.send_message(
                ctx.t("ui.sheet.lore_no_tags"),
                ephemeral=True,
            )

        async with db.execute(
            "SELECT tag_id FROM personagem_tags WHERE personagem_id = ?",
            (self.personagem_id,),
        ) as cursor:
            tag_ids = [row[0] for row in await cursor.fetchall()]

        if not tag_ids:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.lore_no_tags"),
                ephemeral=True,
            )

        tag_placeholders = ", ".join(["?"] * len(tag_ids))
        is_admin = interaction.user.guild_permissions.administrator
        params = list(tag_ids)
        privacy_clause = ""
        if not is_admin:
            privacy_clause = " AND (le.is_private = 0 OR le.is_private IS NULL OR le.owner_id = ?)"
            params.append(interaction.user.id)

        query = f"""
            SELECT le.id, le.titulo, le.resumo, le.conteudo, GROUP_CONCAT(lt.nome, ', ')
            FROM lore_entries le
            JOIN lore_entry_tags let ON let.lore_entry_id = le.id
            JOIN lore_tags lt ON lt.id = let.tag_id
            WHERE let.tag_id IN ({tag_placeholders})
            {privacy_clause}
            GROUP BY le.id
            ORDER BY le.id ASC
        """
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.lore_none_found"),
                ephemeral=True,
            )

        embeds: list[discord.Embed] = []
        for entry_id, titulo, resumo, conteudo, tags in rows:
            partes = _split_text(conteudo or resumo or "", 3900)
            total = len(partes)
            for index, parte in enumerate(partes, start=1):
                sufixo = f" (parte {index}/{total})" if total > 1 else ""
                embed = discord.Embed(
                    title=f"📚 [{entry_id}] {titulo}{sufixo}",
                    description=parte or "—",
                    color=0x2E7D32,
                )
                if tags:
                    embed.add_field(name=ctx.t("ui.sheet.lore_tags"), value=tags, inline=False)
                _set_footer_timestamp(embed, ctx.t("ui.sheet.lore_footer"), ctx=ctx)
                embeds.append(embed)

        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

class FichaView(BaseRPGView):
    def __init__(self, bot, personagem_id, user_id_dono, locale: str | None = None):
        super().__init__(bot, user_id_dono, timeout=None)
        self.personagem_id = personagem_id
        self.locale = resolve_locale(locale)
        self._mark_static_items()
        self._apply_labels()
        self.update_buttons_state("geral")
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.message = interaction.message
        return await super().interaction_check(interaction)

    def _apply_labels(self) -> None:
        label_map = {
            "btn_geral": ("geral", "ui.sheet.general"),
            "btn_combate": ("combate", "ui.sheet.combat"),
            "btn_magia": ("magia", "ui.sheet.magic_alchemy"),
            "btn_atributos": ("atributos", "ui.sheet.attributes_nav"),
            "btn_acoes_padrao": ("acoes", "ui.sheet.standard_actions"),
            "btn_inventario": ("inventario", "ui.sheet.inventory"),
            "btn_buscar": ("buscar", "ui.sheet.search_skill"),
            "btn_add_skill": ("nova_skill", "ui.sheet.new_skill"),
            "btn_gerenciar": ("gerenciar", "ui.sheet.manage"),
        }
        for child in self.children:
            if not isinstance(child, ui.Button):
                continue

            # Handle both direct function and _ViewCallback wrapper
            callback = child.callback
            if hasattr(callback, "callback"):  # _ViewCallback wrapper
                callback = callback.callback

            callback_name = callback.__name__
            if callback_name in label_map:
                key, i18n_key = label_map[callback_name]
                child.label = translate(i18n_key, locale=self.locale)
                child.view_key = key

    def _mark_static_items(self):
        for item in self.children:
            item.is_static = True

    def update_buttons_state(self, mode: str):
        navigation_map = {
            "Geral": "geral",
            "Combate": "combate",
            "Atributos": "atributos",
            "Magia/Alquimia": "magia",
            "Ações Padrão": "acoes",
            "Inventário": "inventario",
        }
        apply_navigation_state(self, mode, navigation_map)
        for item in self.children:
            if not isinstance(item, ui.Button) or not item.label:
                continue
            if item.label == "Buscar Perícia":
                item.disabled = (mode != "geral")
                item.style = discord.ButtonStyle.primary if mode == "geral" else discord.ButtonStyle.secondary
            elif item.label in {"Nova Skill", "Gerenciar"}:
                item.disabled = (mode != "magia")
                item.style = discord.ButtonStyle.success if item.label == "Nova Skill" and mode == "magia" else discord.ButtonStyle.secondary

    # --- NAVEGAÇÃO (ROW 0) ---
    @ui.button(label="Geral", emoji="📜", style=discord.ButtonStyle.secondary, row=0)
    async def btn_geral(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_info_geral(interaction)

    @ui.button(label="Combate", emoji="⚔️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_combate(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_combate(interaction)

    @ui.button(label="Magia/Alquimia", emoji="✨", style=discord.ButtonStyle.secondary, row=0)
    async def btn_magia(self, interaction: discord.Interaction, button: ui.Button):
        await self.atualizar_botoes_habilidade(interaction)

    @ui.button(label="Atributos", emoji="🎯", style=discord.ButtonStyle.secondary, row=0)
    async def btn_atributos(self, interaction: discord.Interaction, button: ui.Button):
        await self.atualizar_botoes_atributos(interaction)

    @ui.button(label="Ações Padrão", emoji="🎬", style=discord.ButtonStyle.secondary, row=0)
    async def btn_acoes_padrao(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_acoes_padrao(interaction)

    @ui.button(label="Inventário", emoji="🎒", style=discord.ButtonStyle.secondary, row=1)
    async def btn_inventario(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_inventario(interaction)

    # --- AÇÕES (ROW 1) ---
    @ui.button(label="Buscar Perícia", emoji="🔎", style=discord.ButtonStyle.secondary, row=1)
    async def btn_buscar(self, interaction: discord.Interaction, button: ui.Button):
        ctx = get_interaction_context(interaction)
        await interaction.response.send_modal(BuscarPericiaModal(self.personagem_id, locale=ctx.locale))

    @ui.button(label="Nova Skill", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def btn_add_skill(self, interaction: discord.Interaction, button: ui.Button):
        ctx = get_interaction_context(interaction)
        await interaction.response.send_modal(NovaHabilidadeModal(self.personagem_id, self, locale=ctx.locale))

    @ui.button(label="Gerenciar", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def btn_gerenciar(self, interaction: discord.Interaction, button: ui.Button):
        ctx = get_interaction_context(interaction)
        skill_repo = SkillRepository(interaction.client.db)
        skills = await skill_repo.list_skills(self.personagem_id)

        if not skills:
            return await interaction.response.send_message(ctx.t("ui.sheet.no_skills_to_manage"), ephemeral=True)

        view_gerenciar = GerenciarHabilidadesView(skills, self, locale=ctx.locale)
        await interaction.response.send_message(
            ctx.t("ui.sheet.select_skill_manage"),
            view=view_gerenciar,
            ephemeral=True,
        )

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        self.update_buttons_state("geral")
        
        db = interaction.client.db
        ctx = get_interaction_context(interaction)
        embed = await construir_embed_ficha(
            db,
            self.personagem_id,
            interaction.user.id,
            locale=ctx.locale,
        )
        if not embed:
            return

        self.clear_dynamic_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _aplicar_identidade_visual(self, interaction: discord.Interaction, embed: discord.Embed) -> None:
        character_repo = CharacterRepository(interaction.client.db)
        identidade = await character_repo.fetch_identity(self.personagem_id)
        if not identidade:
            return
        nome, raca, classe, genero, imagem_url = identidade
        ctx = get_interaction_context(interaction)
        _apply_embed_identity(embed, nome, classe, raca, genero, imagem_url, ctx)

    async def atualizar_botoes_habilidade(self, interaction: discord.Interaction, target_message: discord.Message = None):
        self.update_buttons_state("magia")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)
        skill_repo = SkillRepository(interaction.client.db)

        # Optimization: Parallelize independent DB queries
        recursos, skills, itens = await asyncio.gather(
            character_repo.fetch_resources(self.personagem_id),
            skill_repo.list_skills_for_sheet(self.personagem_id, limit=15),
            inventory_repo.list_potions(interaction.user.id),
        )

        if not recursos:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        vigor_atual, vigor_max, toxicidade_atual, toxicidade_max = recursos
        if vigor_atual is None: vigor_atual = vigor_max
        if toxicidade_atual is None: toxicidade_atual = 0

        potions = [
            (item_id, nome, efeito)
            for item_id, nome, tipo, efeito in itens
            if (tipo and "poção" in tipo.lower())
            or (tipo and "pocao" in tipo.lower())
            or (tipo and "potion" in tipo.lower())
            or (nome and "poção" in nome.lower())
            or (nome and "pocao" in nome.lower())
        ]

        embed = discord.Embed(title=ctx.t("ui.sheet.magic_title"), color=0x8E7CC3)
        vigor_bar = gerar_barra(vigor_atual, vigor_max, segmentos=5)
        embed.add_field(name=ctx.t("ui.sheet.vigor"), value=f"{vigor_bar} {vigor_atual}/{vigor_max}", inline=True)
        embed.add_field(name=ctx.t("ui.sheet.toxicity"), value=f"{toxicidade_atual}/{toxicidade_max}", inline=True)

        if not skills:
            embed.add_field(
                name=ctx.t("ui.sheet.signals_spells"),
                value=ctx.t("ui.sheet.no_skills_learned"),
                inline=False,
            )
        else:
            embed.add_field(
                name=ctx.t("ui.sheet.signals_spells"),
                value=ctx.t("ui.sheet.skills_hint"),
                inline=False,
            )

        for nome, dado, desc in skills:
            self.add_item(
                HabilidadeButton(
                    nome,
                    dado,
                    desc,
                    personagem_id=self.personagem_id,
                    vigor_cost=1,
                    locale=ctx.locale,
                )
            )

        if potions:
            embed.add_field(
                name=ctx.t("ui.sheet.potions"),
                value=ctx.t("ui.sheet.potions_available", count=len(potions)),
                inline=False
            )
            self.add_item(PocaoSelect(potions, self.personagem_id, locale=ctx.locale))
        else:
            embed.add_field(name=ctx.t("ui.sheet.potions"), value=ctx.t("ui.sheet.no_potions"), inline=False)

        _set_footer_timestamp(embed, ctx.t("ui.sheet.magic_footer"), ctx=ctx)

        if target_message:
            await target_message.edit(embed=embed, view=self)
            return

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_cronicas(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        self.update_buttons_state("cronicas")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        dados = await character_repo.fetch_embed_details(self.personagem_id)

        if not dados:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        nome, _, classe, _, historia, img, _, _, _, _, _, _, _, _, _, _, _, _ = dados
        titulo = classe or ctx.t("ui.common.no_title")
        resumo_historia = (historia or "").strip()
        if not resumo_historia:
            resumo_historia = ctx.t("ui.sheet.no_story")
        elif len(resumo_historia) > 600:
            resumo_historia = f"{resumo_historia[:600]}..."

        embed = discord.Embed(
            title=ctx.t("ui.sheet.chronicles_title"),
            description=f"**{nome}** — {titulo}",
            color=0x8B5E34,
        )
        embed.add_field(name=ctx.t("ui.sheet.chronicles_path"), value=resumo_historia, inline=False)

        async with interaction.client.db.execute(
            """
            SELECT id, conteudo
            FROM memoria_campanha
            WHERE conteudo LIKE ?
            ORDER BY id DESC
            LIMIT 3
            """,
            (f"%{nome}%",),
        ) as cursor:
            mencoes = await cursor.fetchall()

        if mencoes:
            linhas = []
            for evento_id, conteudo in mencoes:
                trecho = conteudo[:140] + ("..." if len(conteudo) > 140 else "")
                linhas.append(f"• **[{evento_id}]** {trecho}")
            embed.add_field(name=ctx.t("ui.sheet.recent_mentions"), value="\n".join(linhas), inline=False)
        else:
            embed.add_field(
                name=ctx.t("ui.sheet.recent_mentions"),
                value=ctx.t("ui.sheet.no_mentions"),
                inline=False,
            )

        if img:
            embed.set_thumbnail(url=img)
        _set_footer_timestamp(embed, ctx.t("ui.sheet.chronicles_footer"), ctx=ctx)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_combate(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        self.update_buttons_state("combate")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)

        # Optimization: Parallelize independent DB queries
        dados, itens = await asyncio.gather(
            character_repo.fetch_combat_stats(self.personagem_id),
            inventory_repo.list_items_with_effects(interaction.user.id),
        )

        if not dados:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        hp_atual, hp_max, ataque, defesa = dados
        if hp_atual is None:
            hp_atual = hp_max

        armas = []
        armaduras = []
        for nome, tipo, efeito in itens:
            tipo_lower = (tipo or "").lower()
            nome_lower = (nome or "").lower()
            if "arma" in tipo_lower or "weapon" in tipo_lower:
                armas.append((nome, efeito))
            if "armadura" in tipo_lower or "armor" in tipo_lower or "escudo" in nome_lower:
                armaduras.append((nome, efeito))

        armas_txt = (
            "\n".join([f"• **{n}** — {e or ctx.t('ui.common.no_effect')}" for n, e in armas])
            or ctx.t("ui.common.no_items")
        )
        armaduras_txt = (
            "\n".join([f"• **{n}** — {e or ctx.t('ui.common.no_effect')}" for n, e in armaduras])
            or ctx.t("ui.common.no_items")
        )

        hp_bar = gerar_barra(hp_atual, hp_max, segmentos=5)
        embed = discord.Embed(title=ctx.t("ui.sheet.combat_title"), color=_cor_por_hp(hp_atual, hp_max))
        embed.add_field(name=ctx.t("ui.sheet.life"), value=f"{hp_bar} {hp_atual}/{hp_max}", inline=True)
        embed.add_field(name=ctx.t("ui.sheet.attack"), value=str(ataque), inline=True)
        embed.add_field(name=ctx.t("ui.sheet.current_sp"), value=str(defesa), inline=True)
        embed.add_field(name=ctx.t("ui.sheet.weapons"), value=armas_txt, inline=False)
        embed.add_field(name=ctx.t("ui.sheet.armor"), value=armaduras_txt, inline=False)
        embed.add_field(name=ctx.t("ui.sheet.critical_wounds"), value=ctx.t("ui.sheet.critical_wounds_hint"), inline=False)

        self.add_item(RolagemCombateButton(ctx.t("ui.sheet.roll_to_hit"), "🎯", self.personagem_id, "1d20+{ataque}", locale=ctx.locale))
        self.add_item(RolagemCombateButton(ctx.t("ui.sheet.roll_damage"), "💥", self.personagem_id, "1d6+{ataque}", locale=ctx.locale))
        self.add_item(FerimentosCriticosSelect(locale=ctx.locale))

        _set_footer_timestamp(embed, ctx.t("ui.sheet.combat_footer"), ctx=ctx)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_acoes_padrao(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        self.update_buttons_state("acoes")
        self.clear_dynamic_buttons()

        rolls_repo = RollsRepository(interaction.client.db)
        rolagens = await rolls_repo.list_rolls(self.personagem_id)

        embed = discord.Embed(title=ctx.t("ui.sheet.standard_actions_title"), color=0x3D5A80)
        if not rolagens:
            embed.description = ctx.t("ui.sheet.no_standard_rolls")
        else:
            linhas = [
                f"• **{nome}** `{formula}`" + (f" _({categoria})_" if categoria else "")
                for _, nome, formula, categoria, _ in rolagens
            ]
            embed.add_field(name=ctx.t("ui.sheet.rolls"), value="\n".join(linhas), inline=False)

            for _, nome, formula, _, _ in rolagens:
                self.add_item(RolagemPadraoButton(nome, "🎲", self.personagem_id, formula, locale=ctx.locale))

        _set_footer_timestamp(embed, ctx.t("ui.sheet.standard_actions_footer"), ctx=ctx)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_inventario(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        self.update_buttons_state("inventario")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)

        # Optimization: Parallelize independent DB queries
        itens, nivel = await asyncio.gather(
            inventory_repo.list_items(interaction.user.id),
            character_repo.fetch_level(self.personagem_id),
        )
        nivel = nivel if nivel is not None else 1

        if not itens:
            descricao = ctx.t("ui.sheet.inventory_empty")
        else:
            descricao = "\n".join([
                f"• **{nome}** ({tipo}) — 💰 {ctx.format_currency(valor)}\n  {efeito or ctx.t('ui.common.no_effect')}"
                for nome, tipo, valor, efeito in itens[:20]
            ])

        encumbrance = len(itens)
        capacidade = 10 + (nivel * 2)
        barra_encumbrance = _gerar_barra_encumbrance(encumbrance, capacidade)

        embed = discord.Embed(title=ctx.t("ui.sheet.inventory_title"), description=descricao, color=0xC9B78C)
        embed.add_field(
            name=ctx.t("ui.sheet.encumbrance"),
            value=f"{barra_encumbrance} {ctx.t('ui.sheet.encumbrance_hint', value=f'{encumbrance}/{capacidade}')}",
            inline=False,
        )
        _set_footer_timestamp(embed, ctx.t("ui.sheet.inventory_footer"), ctx=ctx)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_botoes_atributos(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        self.update_buttons_state("atributos")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        atributos = await character_repo.list_attributes(self.personagem_id)
        atributos_map = {nome: valor for nome, valor in atributos}
        derived_stats = character_repo.calculate_derived_stats(atributos_map)

        embed = discord.Embed(title=ctx.t("ui.sheet.attributes_title"), color=0x5865f2)
        if not atributos:
            embed.description = ctx.t("ui.sheet.no_attributes")
        else:
            embed.description = ctx.t("ui.sheet.attributes_hint")
            for nome, valor in atributos:
                self.add_item(AtributoButton(nome, valor, locale=ctx.locale))
            embed.add_field(
                name=ctx.t("ui.sheet.attributes"),
                value=_format_dual_column(atributos, name_width=10, value_width=3, ctx=ctx),
                inline=True
            )
            embed.add_field(
                name=ctx.t("ui.sheet.derived"),
                value=_format_dual_column(
                    [
                        ("Stun", derived_stats["Stun"]),
                        ("Run", derived_stats["Run"]),
                        ("Leap", derived_stats["Leap"]),
                        ("HP", derived_stats["HP"]),
                        ("Stamina", derived_stats["Stamina"]),
                        ("Vigor", derived_stats["Vigor"]),
                        ("Recovery", derived_stats["Recovery"]),
                    ],
                    name_width=9,
                    value_width=5,
                    ctx=ctx,
                ),
                inline=True,
            )
        self.add_item(ExplorarConhecimentoButton(self.personagem_id, locale=ctx.locale))

        _set_footer_timestamp(embed, ctx.t("ui.sheet.attributes_footer"), ctx=ctx)

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_minha_lore(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        character_repo = CharacterRepository(interaction.client.db)
        dados = await character_repo.fetch_embed_details(self.personagem_id)

        if not dados:
            return await interaction.response.send_message(
                ctx.t("ui.sheet.character_not_found"),
                ephemeral=True,
            )

        nome, _, classe, _, historia, img, _, _, _, _, _, _, _, _, _, _, _, _ = dados
        titulo = classe or ctx.t("ui.common.no_title")
        historia = (historia or "").strip()

        if not historia:
            embed = discord.Embed(
                title=ctx.t("ui.sheet.my_lore_title", name=nome),
                description=ctx.t("ui.sheet.lore_unregistered"),
                color=0x5C7AEA,
            )
            if img:
                embed.set_thumbnail(url=img)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if len(historia) <= 3800:
            embed = discord.Embed(
                title=ctx.t("ui.sheet.my_lore_title", name=nome),
                description=historia,
                color=0x5C7AEA,
            )
            embed.set_author(name=f"{nome}, {titulo}")
            if img:
                embed.set_thumbnail(url=img)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        buffer = io.BytesIO(historia.encode("utf-8"))
        arquivo = discord.File(fp=buffer, filename=f"lore_{nome}.txt")
        return await interaction.response.send_message(
            content=ctx.t("ui.sheet.lore_file", name=nome, title=titulo),
            file=arquivo,
            ephemeral=True,
        )
    async def mostrar_diario(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        db = interaction.client.db
        async with db.execute(
            """
            SELECT id, tipo, conteudo
            FROM memoria_campanha
            WHERE tipo IN ('Evento', 'Resumo', 'Quest', 'Consequence')
            ORDER BY id DESC
            LIMIT 20
            """
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            mensagem = ctx.t("ui.sheet.campaign_log_empty")
            if interaction.response.is_done():
                return await interaction.followup.send(mensagem, ephemeral=True)
            return await interaction.response.send_message(mensagem, ephemeral=True)

        linhas = []
        for entry_id, tipo, conteudo in reversed(rows):
            conteudo_curto = _resumir_texto(conteudo, 150)
            linhas.append(f"**[{entry_id}] {tipo}** — {conteudo_curto}")

        texto = "\n".join(linhas)
        embeds = []
        for parte in _split_text(texto, 3800):
            embed = discord.Embed(
                title=ctx.t("ui.sheet.campaign_log_title"),
                description=parte or "—",
                color=0xA84300,
            )
            embed.set_footer(text=ctx.t("ui.sheet.campaign_log_footer"))
            embeds.append(embed)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

    def clear_dynamic_buttons(self):
        items_to_keep = [item for item in self.children if getattr(item, "is_static", False)]
        self.clear_items()
        for item in items_to_keep:
            self.add_item(item)
