import asyncio
import io
import time
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
from ui.views import ConfirmarExclusaoView
from utils import rolar_dados, rolar_pericia_explosiva, gerar_barra
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

def _format_dual_column(items, name_width=12, value_width=5):
    if not items:
        return "_Nenhum registrado._"

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


def _format_list(items, prefix="• "):
    if not items:
        return "_Nenhum registrado._"
    return "\n".join([f"{prefix}{item}" for item in items])


def _format_percentual(atual, maximo):
    if maximo <= 0:
        return "0%"
    pct = max(min(atual / maximo, 1), 0)
    return f"{int(round(pct * 100))}%"


def _format_receitas_conhecidas(receitas):
    if not receitas:
        return "_Nenhuma receita desbloqueada._"
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


def _set_footer_timestamp(embed: discord.Embed, texto_base: str = "") -> None:
    timestamp = f"<t:{int(time.time())}:R>"
    if texto_base:
        embed.set_footer(text=f"{texto_base} • Atualizado {timestamp}")
    else:
        embed.set_footer(text=f"Atualizado {timestamp}")


def _build_author_name(
    nome: Optional[str],
    classe: Optional[str],
    raca: Optional[str],
    genero: Optional[str],
) -> str:
    identity_bits = [item for item in (classe, raca, genero) if item]
    if nome and identity_bits:
        return f"{nome} • {' / '.join(identity_bits)}"
    if nome:
        return nome
    if identity_bits:
        return " • ".join(identity_bits)
    return "Ficha de Personagem"


def _apply_embed_identity(
    embed: discord.Embed,
    nome: Optional[str],
    classe: Optional[str],
    raca: Optional[str],
    genero: Optional[str],
    imagem_url: Optional[str],
) -> None:
    author_name = _build_author_name(nome, classe, raca, genero)
    embed.set_author(name=f"📜 {author_name}")
    thumbnail_url = imagem_url or settings.default_character_thumbnail_url
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)


def _apply_embed_metadata(
    embed: discord.Embed,
    titulo: Optional[str],
    imagem_url: Optional[str],
    footer_text: str,
) -> None:
    embed.set_author(name=titulo or "Sem título")
    thumbnail_url = imagem_url or DEFAULT_THUMBNAIL_URL
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    _set_footer_timestamp(embed, footer_text)


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


async def _table_exists(db, table: str) -> bool:
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ) as cursor:
        return await cursor.fetchone() is not None


async def construir_embed_ficha(db, personagem_id, user_id):
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

    embed = discord.Embed(
        title=f"📜 {nome}",
        color=_cor_por_hp(hp_atual, hp_max),
    )
    _apply_embed_identity(embed, nome, classe, raca, genero, img)
    identidade_partes = []
    if classe:
        identidade_partes.append(f"*{classe}*")
    if raca:
        identidade_partes.append(f"**{raca}**")
    if genero:
        identidade_partes.append(genero)
    identidade_texto = " • ".join(identidade_partes) if identidade_partes else "Identidade indisponível"
    embed.add_field(
        name="📖 Identidade",
        value=f"{identidade_texto} • Nível **{nivel}**",
        inline=False,
    )
    embed.add_field(
        name="📝 História",
        value=historia or "_Sem registro._",
        inline=False,
    )
    embed.add_field(name="📍 Localização", value=local or "Desconhecida", inline=True)
    embed.add_field(name="💰 Ouro", value=str(ouro), inline=True)
    embed.add_field(name="🧭 XP Atual", value=str(xp_atual), inline=True)

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
    embed.add_field(name="Recursos", value=recursos, inline=True)
    embed.add_field(
        name="⚔️ Combate & Magia",
        value=f"Ataque **{ataque}** • Defesa **{defesa}** • MP **{mp_max}**",
        inline=True
    )
    embed.add_field(
        name="🧠 Atributos",
        value=_format_dual_column(atributos, name_width=10, value_width=3),
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
        name="📊 Derivados",
        value=_format_dual_column(derived_items, name_width=9, value_width=5),
        inline=True
    )
    embed.add_field(
        name="✨ Perícias & Sinais",
        value=_format_dual_column(pericias_formatadas, name_width=12, value_width=6),
        inline=True
    )
    embed.add_field(
        name="🎒 Equipamentos em Destaque",
        value=_format_list(itens_formatados),
        inline=False
    )

    _set_footer_timestamp(embed, "Ficha estilo pergaminho • Visual inspirado em crônicas de bruxos")
    return embed

# ==============================================================================
# 1. MODAIS (CRIAR E EDITAR)
# ==============================================================================

class NovaHabilidadeModal(ui.Modal, title="✨ Nova Habilidade"):
    def __init__(self, personagem_id, view_pai):
        super().__init__()
        self.personagem_id = personagem_id
        self.view_pai = view_pai

    nome = ui.TextInput(label="Nome da Habilidade", placeholder="Ex: Bola de Fogo")
    dado = ui.TextInput(label="Dano/Efeito (Dados)", placeholder="Ex: 4d6 (Deixe vazio se não tiver)", required=False)
    descricao = ui.TextInput(
        label="Descrição",
        style=discord.TextStyle.paragraph,
        required=False,
        placeholder="Ex: Dispara uma esfera flamejante..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.dado.value:
            detalhes, _ = rolar_dados(self.dado.value)
            if detalhes is None:
                return await interaction.response.send_message("❌ Fórmula inválida. Use ex: `1d20+5` ou `10`", ephemeral=True)

        skill_repo = SkillRepository(interaction.client.db)
        await skill_repo.add_skill(self.personagem_id, self.nome.value, self.descricao.value, self.dado.value)
        
        await interaction.response.send_message(f"✅ Habilidade **{self.nome.value}** aprendida!", ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

class EditarHabilidadeModal(ui.Modal, title="✏️ Editar Habilidade"):
    def __init__(self, skill_id, current_nome, current_dado, current_desc, view_pai):
        super().__init__()
        self.skill_id = skill_id
        self.view_pai = view_pai
        
        self.nome_input = ui.TextInput(label="Nome", default=current_nome)
        self.dado_input = ui.TextInput(label="Dano/Efeito", default=current_dado, required=False)
        self.desc_input = ui.TextInput(label="Descrição", default=current_desc, style=discord.TextStyle.paragraph, required=False)
        
        self.add_item(self.nome_input)
        self.add_item(self.dado_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.dado_input.value:
            detalhes, _ = rolar_dados(self.dado_input.value)
            if detalhes is None:
                return await interaction.response.send_message("❌ Fórmula inválida.", ephemeral=True)

        skill_repo = SkillRepository(interaction.client.db)
        await skill_repo.update_skill(self.skill_id, self.nome_input.value, self.dado_input.value, self.desc_input.value)
        
        await interaction.response.send_message(f"✅ Habilidade **{self.nome_input.value}** atualizada!", ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

class RolarPericiaModal(ui.Modal, title="🎯 Rolagem de Perícia"):
    def __init__(self, atributo_nome: str, atributo_valor: int):
        super().__init__()
        self.atributo_nome = atributo_nome
        self.atributo_valor = atributo_valor
        self.dcs = {
            "Fácil": 10,
            "Média": 15,
            "Difícil": 20,
            "Extrema": 25,
        }

        self.pericia_nome = ui.TextInput(
            label="Nome da Perícia (opcional)",
            required=False,
            placeholder="Ex: Atletismo (ou deixe vazio)"
        )
        self.pericia_valor = ui.TextInput(
            label="Valor da Perícia",
            placeholder="Ex: 4 (Deixe vazio para 0)",
            required=False
        )
        self.dificuldade_input = ui.TextInput(
            label="DC / Nível de Dificuldade (opcional)",
            required=False,
            placeholder="Ex: 15 ou Médio",
        )

        self.add_item(self.pericia_nome)
        self.add_item(self.pericia_valor)
        self.add_item(self.dificuldade_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val_str = self.pericia_valor.value
            pericia_valor = int(val_str) if val_str else 0
        except ValueError:
            return await interaction.response.send_message("❌ Valor da perícia inválido.", ephemeral=True)

        dc_informada = self._parse_dificuldade()

        rolagens, total, direcao = rolar_pericia_explosiva(self.atributo_valor, pericia_valor)
        classificacao = classificar_resultado(total, dc_informada)

        etiqueta = self.pericia_nome.value.strip() if self.pericia_nome.value else "Perícia"
        detalhes_rolagem = ", ".join(map(str, rolagens))
        explosao_txt = ""
        if direcao == 1:
            explosao_txt = " (Explosão para cima)"
        elif direcao == -1:
            explosao_txt = " (Explosão para baixo)"

        embed = discord.Embed(
            title=f"🎯 {etiqueta} - {self.atributo_nome}",
            color=0x2b2d31
        )
        embed.add_field(
            name="Rolagem",
            value=f"[{detalhes_rolagem}]{explosao_txt}",
            inline=False
        )
        embed.add_field(
            name="Fórmula",
            value=f"1d10 + Stat({self.atributo_valor}) + Skill({pericia_valor})",
            inline=False
        )
        if dc_informada is not None:
            embed.add_field(name="DC", value=str(dc_informada), inline=True)
        else:
            tabela_txt = "/".join(map(str, DEFAULT_DC_THRESHOLDS))
            embed.add_field(name="Tabela de Dificuldade", value=tabela_txt, inline=True)
        embed.add_field(name="Total", value=f"# **{total}**", inline=False)
        resultado = self._avaliar_dificuldade(total)
        if resultado:
            embed.add_field(
                name=f"Resultado vs DC {resultado['dc']} ({resultado['rotulo']})",
                value=f"{resultado['texto']} (Margem {resultado['margem']:+})",
                inline=False,
            )
        dcs_texto = "\n".join([f"• **{nome}**: {valor}" for nome, valor in self.dcs.items()])
        embed.add_field(name="📊 DCs de Referência", value=dcs_texto, inline=False)

        if dc_informada is not None:
            margem = total - dc_informada
            if margem < 0:
                nivel = "Falha"
            elif margem == 0:
                nivel = "Vitória Marginal"
            elif margem < 10:
                nivel = "Vitória"
            else:
                nivel = "Crítica"
            embed.add_field(
                name="🎯 Comparação com DC",
                value=f"DC **{dc_informada}** (Diferença: {margem:+d})",
                inline=False
            )
        else:
            if total >= self.dcs["Extrema"]:
                nivel = "Crítica"
            elif total >= self.dcs["Difícil"]:
                nivel = "Vitória Maior"
            elif total >= self.dcs["Média"]:
                nivel = "Vitória"
            elif total >= self.dcs["Fácil"]:
                nivel = "Vitória Marginal"
            else:
                nivel = "Falha"

        embed.add_field(name="🏆 Nível", value=nivel, inline=False)
        embed.add_field(name="Classificação", value=classificacao, inline=False)

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
        }
        dificuldade_normalizada = dificuldade_raw.lower()
        dc = tabela_dificuldade.get(dificuldade_normalizada)
        rotulo = dificuldade_raw.title()
        if dc is None:
            try:
                dc = int(dificuldade_raw)
                rotulo = "Personalizada"
            except ValueError:
                return None

        margem = total - dc
        if margem < 0:
            texto = "Falha"
        elif margem < 5:
            texto = "Vitória Marginal"
        elif margem < 10:
            texto = "Sucesso"
        else:
            texto = "Crítica"

        if dc in tabela_dificuldade.values():
            rotulo = {
                10: "Fácil",
                15: "Médio",
                20: "Difícil",
                25: "Épico",
            }.get(dc, rotulo)

        return {
            "dc": dc,
            "margem": margem,
            "texto": texto,
            "rotulo": rotulo,
        }

class BuscarPericiaModal(ui.Modal, title="🔎 Buscar Perícia"):
    def __init__(self, personagem_id):
        super().__init__()
        self.personagem_id = personagem_id

    termo = ui.TextInput(
        label="Nome ou parte do nome",
        placeholder="Ex: Espada, Esquiva, Igni",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        termo_busca = self.termo.value.strip()
        termo_sql = f"%{termo_busca}%"
        skill_repo = SkillRepository(interaction.client.db)
        resultados = await skill_repo.search_skills(self.personagem_id, termo_sql, limit=5)

        if not resultados:
            embed = discord.Embed(
                title="🔎 Nenhuma perícia encontrada",
                description=f"Não encontramos nada com **'{termo_busca}'**.\n\n💡 **Dica:** Tente buscar por partes do nome (ex: 'Fogo' em vez de 'Bola de Fogo') ou verifique se a habilidade já foi criada na aba **Magia**.",
                color=0xED4245
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title=f"🔎 Resultados para '{self.termo.value}'",
            color=0x5865F2  # Blurple
        )

        for nome, dado, descricao in resultados:
            dado_txt = f" `{dado}`" if dado else ""
            resumo = (descricao[:100] + "...") if descricao and len(descricao) > 100 else (descricao or "Sem descrição.")
            embed.add_field(
                name=f"{nome}{dado_txt}",
                value=resumo,
                inline=False
            )

        embed.set_footer(text="Mostrando os 5 primeiros resultados.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==============================================================================
# 2. VIEWS AUXILIARES (GERENCIAMENTO)
# ==============================================================================

class AcoesHabilidadeView(ui.View):
    def __init__(self, skill_id, nome, dado, desc, view_ficha):
        super().__init__(timeout=60)
        self.skill_id = skill_id
        self.nome = nome
        self.dado = dado
        self.desc = desc
        self.view_ficha = view_ficha

    @ui.button(label="Editar", emoji="✏️", style=discord.ButtonStyle.primary)
    async def btn_editar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            EditarHabilidadeModal(self.skill_id, self.nome, self.dado, self.desc, self.view_ficha)
        )

    @ui.button(label="Excluir", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def btn_excluir(self, interaction: discord.Interaction, button: ui.Button):
        async def confirmar(itx: discord.Interaction):
            skill_repo = SkillRepository(itx.client.db)
            await skill_repo.delete_skill(self.skill_id)

            await itx.response.edit_message(content=f"🗑️ Habilidade **{self.nome}** removida.", view=None)
            await self.view_ficha.atualizar_botoes_habilidade(itx)

        async def cancelar(itx: discord.Interaction):
            view_restore = AcoesHabilidadeView(self.skill_id, self.nome, self.dado, self.desc, self.view_ficha)
            await itx.response.edit_message(
                content=f"🛠️ Gerenciando: **{self.nome}**\nO que deseja fazer?",
                view=view_restore
            )

        view_conf = ConfirmarExclusaoView(confirmar, cancel_callback=cancelar)
        await interaction.response.edit_message(
            content=f"⚠️ Tem certeza que deseja excluir a habilidade **{self.nome}**?",
            view=view_conf
        )
        # Não chamamos self.stop() aqui porque queremos que esta view continue ativa
        # caso o usuário cancele (embora neste caso a view seja substituída na mensagem)
        # Como substituímos a mensagem, esta view (AcoesHabilidadeView) não receberá mais eventos daquela mensagem específica.
        self.stop()

class SelecionarHabilidadeSelect(ui.Select):
    def __init__(self, skills, view_ficha):
        self.skills_map = {str(s[0]): s for s in skills}
        
        options = []
        for id_skill, nome, dado, desc in skills:
            desc_curta = f"({dado}) " if dado else ""
            desc_curta += desc[:50] if desc else "Sem descrição"
            
            # UX Improvement: Use consistent emojis for skill types
            emoji = "🎲" if dado else "✨"

            options.append(discord.SelectOption(
                label=nome[:100], 
                value=str(id_skill), 
                description=desc_curta[:100],
                emoji=emoji
            ))

        super().__init__(placeholder="✨ Escolha uma habilidade para gerenciar...", min_values=1, max_values=1, options=options)
        self.view_ficha = view_ficha

    async def callback(self, interaction: discord.Interaction):
        skill_id = self.values[0]
        data = self.skills_map.get(skill_id)
        if not data:
            return await interaction.response.send_message("❌ Habilidade não encontrada.", ephemeral=True)
            
        id_skill, nome, dado, desc = data
        
        view = AcoesHabilidadeView(id_skill, nome, dado, desc, self.view_ficha)
        await interaction.response.send_message(
            f"🛠️ Gerenciando: **{nome}**\nO que deseja fazer?", 
            view=view, 
            ephemeral=True
        )

class GerenciarHabilidadesView(ui.View):
    def __init__(self, skills, view_ficha):
        super().__init__(timeout=60)
        self.add_item(SelecionarHabilidadeSelect(skills, view_ficha))

class FerimentosCriticosSelect(ui.Select):
    def __init__(self):
        ferimentos = [
            ("Fratura", "Movimento reduzido e penalidade em testes físicos."),
            ("Sangramento", "Perde HP por turno até estancar."),
            ("Concussão", "Penalidade em Percepção e Magia."),
            ("Perfuração", "Ações de combate com desvantagem."),
            ("Queimadura", "Resistência reduzida e dor contínua.")
        ]

        options = [
            discord.SelectOption(
                label=nome,
                value=nome,
                description=desc[:100],
                emoji="🩸"
            ) for nome, desc in ferimentos
        ]
        super().__init__(placeholder="🩸 Ferimentos Críticos (tabela)", min_values=1, max_values=1, options=options)
        self.ferimentos_map = {nome: desc for nome, desc in ferimentos}
        self.row = 3

    async def callback(self, interaction: discord.Interaction):
        ferimento = self.values[0]
        desc = self.ferimentos_map.get(ferimento, "Sem detalhes.")
        embed = discord.Embed(title=f"🩸 {ferimento}", description=desc, color=0x8B1A1A)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class FerimentosCriticosView(ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(FerimentosCriticosSelect())

class PocaoSelect(ui.Select):
    def __init__(self, potions, personagem_id):
        self.personagem_id = personagem_id
        self.potion_map = {str(p[0]): p for p in potions}
        options = [
            discord.SelectOption(
                label=nome[:100],
                value=str(item_id),
                description=(efeito or "Sem efeito")[:100],
                emoji="🧪"
            )
            for item_id, nome, efeito in potions
        ]
        super().__init__(placeholder="🧪 Consumir poção", min_values=1, max_values=1, options=options)
        self.row = 3

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        potion = self.potion_map.get(item_id)
        if not potion:
            return await interaction.response.send_message("❌ Poção não encontrada.", ephemeral=True)

        _, nome, efeito = potion
        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)
        row = await character_repo.fetch_toxicity(self.personagem_id)

        if not row:
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

        toxicidade_atual, toxicidade_max = row
        custo_toxicidade = 10
        nova_toxicidade = min((toxicidade_atual or 0) + custo_toxicidade, toxicidade_max or 100)

        await character_repo.update_toxicity(self.personagem_id, nova_toxicidade)
        await inventory_repo.delete_item(item_id)

        embed = discord.Embed(
            title=f"🧪 {interaction.user.display_name} consumiu {nome}",
            description=efeito or "Efeito não descrito.",
            color=0x4B7B6F
        )

        pct = nova_toxicidade / toxicidade_max if toxicidade_max > 0 else 0
        if pct <= 0.3:
            cor = "🟩"
        elif pct <= 0.6:
            cor = "🟨"
        else:
            cor = "🟥"
        tox_bar = gerar_barra(nova_toxicidade, toxicidade_max, tamanho=5, cor_cheio=cor)

        embed.add_field(name="☠️ Toxicidade", value=f"{tox_bar} +{custo_toxicidade} ({nova_toxicidade}/{toxicidade_max})")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PocaoView(ui.View):
    def __init__(self, potions, personagem_id):
        super().__init__(timeout=120)
        self.add_item(PocaoSelect(potions, personagem_id))

# ==============================================================================
# 3. COMPONENTES DA FICHA PRINCIPAL
# ==============================================================================

class HabilidadeButton(ui.Button):
    def __init__(self, nome, dado, descricao, personagem_id=None, vigor_cost=0):
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

    async def callback(self, interaction: discord.Interaction):
        vigor_feedback = None
        if self.personagem_id and self.vigor_cost:
            character_repo = CharacterRepository(interaction.client.db)
            row = await character_repo.fetch_vigor(self.personagem_id)

            if not row:
                return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

            vigor_atual, vigor_max = row
            if vigor_atual is None:
                vigor_atual = vigor_max

            if vigor_atual < self.vigor_cost:
                return await interaction.response.send_message(
                    "⚠️ Vigor insuficiente para conjurar.",
                    ephemeral=True
                )

            novo_vigor = max(vigor_atual - self.vigor_cost, 0)
            await character_repo.update_vigor(self.personagem_id, novo_vigor)

            # Palette: Add visual feedback for Vigor cost
            bar = gerar_barra(novo_vigor, vigor_max, tamanho=5)
            vigor_feedback = f"Vigor: {bar} {novo_vigor}/{vigor_max}"

        embed = discord.Embed(title=f"⚔️ {interaction.user.display_name} usou {self.nome_habilidade}", color=0xFF5500)
        embed.description = self.desc_habilidade or "..."

        if vigor_feedback:
            embed.set_footer(text=vigor_feedback)
        
        if self.dado_habilidade:
            detalhes, total = rolar_dados(self.dado_habilidade)
            if detalhes:
                embed.add_field(name="🎲 Rolagem", value=f"`{self.dado_habilidade}`\nResult: {detalhes}\n# **{total}**")
        
        await interaction.response.send_message(embed=embed)

class AtributoButton(ui.Button):
    def __init__(self, nome, valor):
        label_btn = f"{nome} ({valor})"
        super().__init__(style=discord.ButtonStyle.secondary, label=label_btn, emoji="🎯", row=None)
        self.nome_atributo = nome
        self.valor_atributo = valor

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RolarPericiaModal(self.nome_atributo, self.valor_atributo))


class RolagemCombateButton(ui.Button):
    def __init__(self, label, emoji, personagem_id, formula_template):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, row=2)
        self.personagem_id = personagem_id
        self.formula_template = formula_template

    async def callback(self, interaction: discord.Interaction):
        character_repo = CharacterRepository(interaction.client.db)
        ataque = await character_repo.fetch_attack(self.personagem_id)

        if ataque is None:
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

        ataque = ataque or 0
        formula = self.formula_template.format(ataque=ataque)
        detalhes, total = rolar_dados(formula)
        if detalhes is None:
            return await interaction.response.send_message("❌ Fórmula inválida.", ephemeral=True)

        embed = discord.Embed(
            title=f"🎲 {interaction.user.display_name} rolou {self.label}",
            description=f"`{formula}`\nResultado: {detalhes}\n**Total: {total}**",
            color=0xB5651D
        )
        await interaction.response.send_message(embed=embed)


class RolagemPadraoButton(ui.Button):
    def __init__(self, label: str, emoji: str, personagem_id: int, formula_template: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji, row=2)
        self.personagem_id = personagem_id
        self.formula_template = formula_template

    async def callback(self, interaction: discord.Interaction):
        character_repo = CharacterRepository(interaction.client.db)
        atributos = await character_repo.list_attributes_dict(self.personagem_id)
        formula_resolvida, missing = resolve_roll_template(self.formula_template, atributos)

        if missing:
            faltantes = ", ".join(sorted(set(missing)))
            return await interaction.response.send_message(
                f"⚠️ Atributos não encontrados na ficha: {faltantes}.",
                ephemeral=True,
            )

        detalhes, total = rolar_dados(formula_resolvida)
        if detalhes is None:
            return await interaction.response.send_message("❌ Fórmula inválida.", ephemeral=True)

        embed = discord.Embed(
            title=f"🎲 {interaction.user.display_name} rolou {self.label}",
            description=f"`{formula_resolvida}`\nResultado: {detalhes}\n**Total: {total}**",
            color=0x3D5A80,
        )
        await interaction.response.send_message(embed=embed)


class ExplorarConhecimentoButton(ui.Button):
    def __init__(self, personagem_id: int):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Explorar Conhecimento",
            emoji="📚",
            row=2,
        )
        self.personagem_id = personagem_id

    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.db
        required_tables = ("lore_entry_tags", "lore_tags", "lore_entries")
        for table in required_tables:
            if not await _table_exists(db, table):
                return await interaction.response.send_message(
                    "⚠️ O sistema de tags de lore ainda não está disponível.",
                    ephemeral=True,
                )

        if not await _table_exists(db, "personagem_tags"):
            return await interaction.response.send_message(
                "⚠️ Nenhuma tag foi associada ao seu personagem ainda.",
                ephemeral=True,
            )

        async with db.execute(
            "SELECT tag_id FROM personagem_tags WHERE personagem_id = ?",
            (self.personagem_id,),
        ) as cursor:
            tag_ids = [row[0] for row in await cursor.fetchall()]

        if not tag_ids:
            return await interaction.response.send_message(
                "⚠️ Nenhuma tag foi associada ao seu personagem ainda.",
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
                "📭 Nenhum lore compatível com as tags do seu personagem foi encontrado.",
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
                    embed.add_field(name="Tags", value=tags, inline=False)
                _set_footer_timestamp(embed, "Explorar Conhecimento")
                embeds.append(embed)

        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

class FichaView(BaseRPGView):
    def __init__(self, bot, personagem_id, user_id_dono):
        super().__init__(bot, user_id_dono, timeout=None)
        self.personagem_id = personagem_id
        self._mark_static_items()
        self.update_buttons_state("geral")

    def _mark_static_items(self):
        for item in self.children:
            item.is_static = True

    def update_buttons_state(self, mode: str):
        for item in self.children:
            if isinstance(item, ui.Button) and item.label:
                if item.label == "Geral":
                    is_active = mode == "geral"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Combate":
                    is_active = mode == "combate"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Atributos":
                    is_active = mode == "atributos"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Magia/Alquimia":
                    is_active = mode == "magia"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Ações Padrão":
                    is_active = mode == "acoes"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Inventário":
                    is_active = mode == "inventario"
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Buscar Perícia":
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
        await interaction.response.send_modal(BuscarPericiaModal(self.personagem_id))

    @ui.button(label="Nova Skill", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def btn_add_skill(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(NovaHabilidadeModal(self.personagem_id, self))

    @ui.button(label="Gerenciar", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def btn_gerenciar(self, interaction: discord.Interaction, button: ui.Button):
        skill_repo = SkillRepository(interaction.client.db)
        skills = await skill_repo.list_skills(self.personagem_id)

        if not skills:
            return await interaction.response.send_message("❌ Você não tem habilidades para gerenciar.", ephemeral=True)

        view_gerenciar = GerenciarHabilidadesView(skills, self)
        await interaction.response.send_message("Selecione a habilidade que deseja editar ou excluir:", view=view_gerenciar, ephemeral=True)

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        self.update_buttons_state("geral")
        
        db = interaction.client.db
        embed = await construir_embed_ficha(db, self.personagem_id, interaction.user.id)
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
        _apply_embed_identity(embed, nome, classe, raca, genero, imagem_url)

    async def atualizar_botoes_habilidade(self, interaction: discord.Interaction):
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
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

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

        embed = discord.Embed(title="✨ Magia & Alquimia", color=0x8E7CC3)
        vigor_bar = gerar_barra(vigor_atual, vigor_max, segmentos=5)
        embed.add_field(name="⚡ Vigor", value=f"{vigor_bar} {vigor_atual}/{vigor_max}", inline=True)
        embed.add_field(name="☠️ Toxicidade", value=f"{toxicidade_atual}/{toxicidade_max}", inline=True)

        if not skills:
            embed.add_field(name="Sinais/Feitiços", value="Nenhuma habilidade aprendida. Clique em '➕ Nova Skill'.", inline=False)
        else:
            embed.add_field(name="Sinais/Feitiços", value="Clique para conjurar (gasta 1 vigor).", inline=False)

        for nome, dado, desc in skills:
            self.add_item(HabilidadeButton(nome, dado, desc, personagem_id=self.personagem_id, vigor_cost=1))

        if potions:
            embed.add_field(
                name="🧪 Poções",
                value=f"{len(potions)} disponíveis (selecione abaixo para consumir).",
                inline=False
            )
            self.add_item(PocaoSelect(potions, self.personagem_id))
        else:
            embed.add_field(name="🧪 Poções", value="Nenhuma poção no inventário.", inline=False)

        _set_footer_timestamp(embed, "Magia & Alquimia")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_cronicas(self, interaction: discord.Interaction):
        self.update_buttons_state("cronicas")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        dados = await character_repo.fetch_embed_details(self.personagem_id)

        if not dados:
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

        nome, _, classe, _, historia, img, _, _, _, _, _, _, _, _, _, _, _, _ = dados
        titulo = classe or "Sem título"
        resumo_historia = (historia or "").strip()
        if not resumo_historia:
            resumo_historia = "_Sem trajetória registrada._"
        elif len(resumo_historia) > 600:
            resumo_historia = f"{resumo_historia[:600]}..."

        embed = discord.Embed(
            title="📖 Crônicas",
            description=f"**{nome}** — {titulo}",
            color=0x8B5E34,
        )
        embed.add_field(name="🧭 Trajetória", value=resumo_historia, inline=False)

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
            embed.add_field(name="📝 Menções recentes", value="\n".join(linhas), inline=False)
        else:
            embed.add_field(
                name="📝 Menções recentes",
                value="_Nenhuma menção recente no diário._",
                inline=False,
            )

        if img:
            embed.set_thumbnail(url=img)
        _set_footer_timestamp(embed, "Crônicas do personagem")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_combate(self, interaction: discord.Interaction):
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
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

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

        armas_txt = "\n".join([f"• **{n}** — {e or 'Sem efeito'}" for n, e in armas]) or "Sem armas equipadas."
        armaduras_txt = "\n".join([f"• **{n}** — {e or 'Sem efeito'}" for n, e in armaduras]) or "Sem armaduras registradas."

        hp_bar = gerar_barra(hp_atual, hp_max, segmentos=5)
        embed = discord.Embed(title="⚔️ Combate", color=_cor_por_hp(hp_atual, hp_max))
        embed.add_field(name="❤️ Vida", value=f"{hp_bar} {hp_atual}/{hp_max}", inline=True)
        embed.add_field(name="⚔️ Ataque", value=str(ataque), inline=True)
        embed.add_field(name="🛡️ SP Atual", value=str(defesa), inline=True)
        embed.add_field(name="Armas", value=armas_txt, inline=False)
        embed.add_field(name="Armadura", value=armaduras_txt, inline=False)
        embed.add_field(name="Ferimentos Críticos", value="Use a tabela interativa abaixo.", inline=False)

        self.add_item(RolagemCombateButton("Roll to Hit", "🎯", self.personagem_id, "1d20+{ataque}"))
        self.add_item(RolagemCombateButton("Roll Damage", "💥", self.personagem_id, "1d6+{ataque}"))
        self.add_item(FerimentosCriticosSelect())

        _set_footer_timestamp(embed, "Combate")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_acoes_padrao(self, interaction: discord.Interaction):
        self.update_buttons_state("acoes")
        self.clear_dynamic_buttons()

        rolls_repo = RollsRepository(interaction.client.db)
        rolagens = await rolls_repo.list_rolls(self.personagem_id)

        embed = discord.Embed(title="🎬 Ações Padrão", color=0x3D5A80)
        if not rolagens:
            embed.description = "Nenhuma rolagem padrão cadastrada para este personagem."
        else:
            linhas = [
                f"• **{nome}** `{formula}`" + (f" _({categoria})_" if categoria else "")
                for _, nome, formula, categoria, _ in rolagens
            ]
            embed.add_field(name="Rolagens", value="\n".join(linhas), inline=False)

            for _, nome, formula, _, _ in rolagens:
                self.add_item(RolagemPadraoButton(nome, "🎲", self.personagem_id, formula))

        _set_footer_timestamp(embed, "Ações padrão da ficha")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_inventario(self, interaction: discord.Interaction):
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
            descricao = "🎒 Seu inventário está vazio.\n\nVisite a **/loja** para comprar equipamentos ou explore o mundo para encontrar tesouros!"
        else:
            descricao = "\n".join([
                f"• **{nome}** ({tipo}) — 💰 {valor}\n  {efeito or 'Sem efeito'}"
                for nome, tipo, valor, efeito in itens[:20]
            ])

        encumbrance = len(itens)
        capacidade = 10 + (nivel * 2)
        barra_encumbrance = _gerar_barra_encumbrance(encumbrance, capacidade)

        embed = discord.Embed(title="🎒 Inventário", description=descricao, color=0xC9B78C)
        embed.add_field(
            name="Encumbrance",
            value=f"{barra_encumbrance} {encumbrance}/{capacidade} (1 por item)",
            inline=False,
        )
        _set_footer_timestamp(embed, "Inventário")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_botoes_atributos(self, interaction: discord.Interaction):
        self.update_buttons_state("atributos")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        atributos = await character_repo.list_attributes(self.personagem_id)
        atributos_map = {nome: valor for nome, valor in atributos}
        derived_stats = character_repo.calculate_derived_stats(atributos_map)

        embed = discord.Embed(title="🎯 Atributos", color=0x5865f2)
        if not atributos:
            embed.description = "Nenhum atributo cadastrado. Use /atributo_definir para criar."
        else:
            embed.description = "Clique em um atributo para rolar uma perícia."
            for nome, valor in atributos:
                self.add_item(AtributoButton(nome, valor))
            embed.add_field(
                name="🧠 Atributos",
                value=_format_dual_column(atributos, name_width=10, value_width=3),
                inline=True
            )
            embed.add_field(
                name="📊 Derivados",
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
                ),
                inline=True,
            )
        self.add_item(ExplorarConhecimentoButton(self.personagem_id))

        _set_footer_timestamp(embed, "Atributos")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_minha_lore(self, interaction: discord.Interaction):
        character_repo = CharacterRepository(interaction.client.db)
        dados = await character_repo.fetch_embed_details(self.personagem_id)

        if not dados:
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

        nome, _, classe, _, historia, img, _, _, _, _, _, _, _, _, _, _, _, _ = dados
        titulo = classe or "Sem título"
        historia = (historia or "").strip()

        if not historia:
            embed = discord.Embed(
                title=f"📚 Minha Lore — {nome}",
                description="_Biografia ainda não registrada._",
                color=0x5C7AEA,
            )
            if img:
                embed.set_thumbnail(url=img)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if len(historia) <= 3800:
            embed = discord.Embed(
                title=f"📚 Minha Lore — {nome}",
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
            content=f"📚 **{nome}, {titulo}** — biografia completa em anexo.",
            file=arquivo,
            ephemeral=True,
        )
    async def mostrar_diario(self, interaction: discord.Interaction):
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
            mensagem = "📭 O diário está vazio. A IA não sabe nada sobre sua história atual."
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
                title="📖 Diário da Campanha",
                description=parte or "—",
                color=0xA84300,
            )
            embed.set_footer(text="Linha do tempo registrada até agora.")
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
