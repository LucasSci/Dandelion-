import asyncio
import time

import discord
from discord import ui
from data.repositories import CharacterRepository, InventoryRepository, SkillRepository
from utils import rolar_dados, rolar_pericia_explosiva
from ui.base_view import BaseRPGView
from ui.views import ConfirmarExclusaoView

# ==============================================================================
# 0. HELPERS (LAYOUT)
# ==============================================================================

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


def _cor_por_hp(hp_atual, hp_max):
    if hp_max <= 0:
        return 0xED4245
    pct = max(min(hp_atual / hp_max, 1), 0)
    if pct > 0.7:
        return 0x57F287
    if pct > 0.3:
        return 0xFEE75C
    return 0xED4245


def _set_footer_timestamp(embed: discord.Embed, texto_base: str = "") -> None:
    timestamp = f"<t:{int(time.time())}:R>"
    if texto_base:
        embed.set_footer(text=f"{texto_base} • Atualizado {timestamp}")
    else:
        embed.set_footer(text=f"Atualizado {timestamp}")


def _split_text(texto: str, limite: int = 3800) -> list[str]:
    texto = (texto or "").strip()
    if not texto:
        return [""]
    return [texto[i : i + limite] for i in range(0, len(texto), limite)]


def _resumir_texto(texto: str, limite: int = 180) -> str:
    texto = (texto or "").strip()
    if len(texto) <= limite:
        return texto
    return f"{texto[:limite]}..."


async def construir_embed_ficha(db, personagem_id, user_id):
    character_repo = CharacterRepository(db)
    inventory_repo = InventoryRepository(db)
    skill_repo = SkillRepository(db)

    dados = await character_repo.fetch_embed_details(personagem_id)

    if not dados:
        return None

    (
        nome, raca, classe, nivel, historia, img, ouro, hp_atual, hp_max, mp_max,
        ataque, defesa, xp_atual, vigor_atual, vigor_max, toxicidade_atual, toxicidade_max, local
    ) = dados
    if hp_atual is None:
        hp_atual = hp_max
    if vigor_atual is None:
        vigor_atual = vigor_max
    if toxicidade_atual is None:
        toxicidade_atual = 0

    atributos, pericias, itens = await asyncio.gather(
        character_repo.list_attributes(personagem_id, limit=12),
        skill_repo.list_skills_for_sheet(personagem_id, limit=10, order_by_name=True),
        inventory_repo.list_recent_items(user_id, limit=8),
    )

    # Using indexing to handle potential extra columns (description) from the repo
    pericias_formatadas = [(p[0], p[1] or "—") for p in pericias]

    itens_formatados = [
        f"**{nome}** ({tipo})" if tipo else f"**{nome}**"
        for nome, tipo in itens
    ]

    embed = discord.Embed(
        title=f"📜 {nome}",
        color=_cor_por_hp(hp_atual, hp_max),
    )
    epiteto = (classe or "").strip()
    titulo_personagem = f"{nome} — {epiteto}" if epiteto else nome
    embed.set_author(name=titulo_personagem)
    embed.add_field(
        name="📖 Identidade",
        value=f"*{classe}* • **{raca}** • Nível **{nivel}**",
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
    recursos = (
        f"❤️ HP {hp_atual}/{hp_max} ({hp_pct})\n"
        f"⚡ Vigor {vigor_atual}/{vigor_max} ({vigor_pct})\n"
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

    if img:
        embed.set_thumbnail(url=img)
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

        self.pericia_nome = ui.TextInput(
            label="Nome da Perícia (opcional)",
            required=False,
            placeholder="Ex: Atletismo (ou deixe vazio)"
        )
        self.pericia_valor = ui.TextInput(
            label="Valor da Perícia",
            placeholder="Ex: 4",
        )

        self.add_item(self.pericia_nome)
        self.add_item(self.pericia_valor)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pericia_valor = int(self.pericia_valor.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valor da perícia inválido.", ephemeral=True)

        rolagens, total, direcao = rolar_pericia_explosiva(self.atributo_valor, pericia_valor)

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
        embed.add_field(name="Total", value=f"# **{total}**", inline=False)

        await interaction.response.send_message(embed=embed)


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
        termo = f"%{self.termo.value.strip()}%"
        skill_repo = SkillRepository(interaction.client.db)
        resultados = await skill_repo.search_skills(self.personagem_id, termo, limit=5)

        if not resultados:
            embed = discord.Embed(
                title="🔎 Nenhuma perícia encontrada",
                description=f"Não encontramos nada com **'{self.termo.value}'**.\n\n💡 **Dica:** Tente buscar por partes do nome (ex: 'Fogo' em vez de 'Bola de Fogo') ou verifique se a habilidade já foi criada na aba **Magia**.",
                color=0xED4245
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        linhas = []
        for nome, dado, descricao in resultados:
            dado_txt = f" ({dado})" if dado else ""
            resumo = (descricao[:80] + "...") if descricao and len(descricao) > 80 else (descricao or "Sem descrição.")
            linhas.append(f"• **{nome}**{dado_txt} — {resumo}")

        await interaction.response.send_message("\n".join(linhas), ephemeral=True)

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

        view_conf = ConfirmarExclusaoView(confirmar)
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
        embed.add_field(name="☠️ Toxicidade", value=f"+{custo_toxicidade} (Total: {nova_toxicidade})")
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

        embed = discord.Embed(title=f"⚔️ {interaction.user.display_name} usou {self.nome_habilidade}", color=0xFF5500)
        embed.description = self.desc_habilidade or "..."
        
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
                    is_active = (mode == "geral")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Combate":
                    is_active = (mode == "combate")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Atributos":
                    is_active = (mode == "atributos")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Magia/Alquimia":
                    is_active = (mode == "magia")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Inventário":
                    is_active = (mode == "inventario")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Crônicas":
                    is_active = (mode == "cronicas")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Buscar Perícia":
                    item.disabled = (mode != "geral")
                    item.style = discord.ButtonStyle.primary if mode == "geral" else discord.ButtonStyle.secondary
                elif item.label in {"Nova Skill", "Gerenciar"}:
                    item.disabled = (mode != "magia")
                    item.style = discord.ButtonStyle.success if item.label == "Nova Skill" and mode == "magia" else discord.ButtonStyle.secondary
                elif item.label in {"Minha Lore", "Diário"}:
                    is_enabled = mode in {"cronicas", "geral"}
                    item.disabled = not is_enabled
                    item.style = discord.ButtonStyle.primary if is_enabled else discord.ButtonStyle.secondary

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

    @ui.button(label="Inventário", emoji="🎒", style=discord.ButtonStyle.secondary, row=0)
    async def btn_inventario(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_inventario(interaction)

    @ui.button(label="Crônicas", emoji="📖", style=discord.ButtonStyle.secondary, row=0)
    async def btn_cronicas(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_cronicas(interaction)

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

    @ui.button(label="Minha Lore", emoji="📚", style=discord.ButtonStyle.secondary, row=1)
    async def btn_minha_lore(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_minha_lore(interaction)

    @ui.button(label="Diário", emoji="📔", style=discord.ButtonStyle.secondary, row=1)
    async def btn_diario(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_diario(interaction)

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        self.update_buttons_state("geral")
        
        db = interaction.client.db
        embed = await construir_embed_ficha(db, self.personagem_id, interaction.user.id)
        if not embed:
            return

        self.clear_dynamic_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

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
            inventory_repo.list_potions(interaction.user.id)
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
        vigor_pct = _format_percentual(vigor_atual, vigor_max)
        embed.add_field(name="⚡ Vigor", value=f"{vigor_atual}/{vigor_max} ({vigor_pct})", inline=True)
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

    async def mostrar_combate(self, interaction: discord.Interaction):
        self.update_buttons_state("combate")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)

        # Optimization: Parallelize independent DB queries
        dados, itens = await asyncio.gather(
            character_repo.fetch_combat_stats(self.personagem_id),
            inventory_repo.list_items_with_effects(interaction.user.id)
        )

        if not dados:
            return await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

        hp_atual, hp_max, ataque, defesa = dados
        if hp_atual is None: hp_atual = hp_max

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

        hp_pct = _format_percentual(hp_atual, hp_max)
        embed = discord.Embed(title="⚔️ Combate", color=_cor_por_hp(hp_atual, hp_max))
        embed.add_field(name="❤️ Vida", value=f"{hp_atual}/{hp_max} ({hp_pct})", inline=True)
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

    async def mostrar_inventario(self, interaction: discord.Interaction):
        self.update_buttons_state("inventario")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        inventory_repo = InventoryRepository(interaction.client.db)

        # Optimization: Parallelize independent DB queries
        itens, nivel = await asyncio.gather(
            inventory_repo.list_items(interaction.user.id),
            character_repo.fetch_level(self.personagem_id)
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
        embed = discord.Embed(title="🎒 Inventário", description=descricao, color=0xC9B78C)
        embed.add_field(name="Encumbrance", value=f"{encumbrance}/{capacidade} (1 por item)", inline=False)
        _set_footer_timestamp(embed, "Layout estilo pergaminho limpo • Lista dinâmica")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_botoes_atributos(self, interaction: discord.Interaction):
        self.update_buttons_state("atributos")
        self.clear_dynamic_buttons()

        character_repo = CharacterRepository(interaction.client.db)
        atributos = await character_repo.list_attributes(self.personagem_id)

        embed = discord.Embed(title="🎯 Atributos", color=0x5865f2)
        if not atributos:
            embed.description = "Nenhum atributo cadastrado. Use /atributo_definir para criar."
        else:
            embed.description = "Clique em um atributo para rolar uma perícia."
            for nome, valor in atributos:
                self.add_item(AtributoButton(nome, valor))

        _set_footer_timestamp(embed, "Atributos")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_cronicas(self, interaction: discord.Interaction):
        self.update_buttons_state("cronicas")
        self.clear_dynamic_buttons()

        db = interaction.client.db

        async def fetch_lore():
            async with db.execute(
                """
                SELECT id, titulo, resumo, conteudo, criado_em
                FROM lore_entries
                ORDER BY id DESC
                LIMIT 4
                """
            ) as cursor:
                return await cursor.fetchall()

        async def fetch_diario():
            async with db.execute(
                """
                SELECT id, tipo, conteudo, data_registro
                FROM memoria_campanha
                ORDER BY id DESC
                LIMIT 4
                """
            ) as cursor:
                return await cursor.fetchall()

        lore_entries, diario_entries = await asyncio.gather(fetch_lore(), fetch_diario())

        embed = discord.Embed(title="📖 Crônicas", color=0x7A5C3E)
        embed.description = "Resumo rápido do lore do mundo e da linha do tempo recente."

        if lore_entries:
            lore_lines = []
            for entry_id, titulo, resumo, conteudo, _ in lore_entries:
                base = resumo or conteudo or "—"
                lore_lines.append(f"**[{entry_id}] {titulo}** — {_resumir_texto(base)}")
            embed.add_field(name="📚 Lore do Mundo", value="\n".join(lore_lines), inline=False)
        else:
            embed.add_field(name="📚 Lore do Mundo", value="Nenhum lore registrado ainda.", inline=False)

        if diario_entries:
            diario_lines = []
            for entry_id, tipo, conteudo, _ in diario_entries:
                base = conteudo or "—"
                diario_lines.append(f"**[{entry_id}] {tipo}** — {_resumir_texto(base)}")
            embed.add_field(name="🕰️ Diário da Campanha", value="\n".join(diario_lines), inline=False)
        else:
            embed.add_field(name="🕰️ Diário da Campanha", value="Nenhuma entrada no diário até agora.", inline=False)

        _set_footer_timestamp(embed, "Crônicas • Lore & Memória")

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_minha_lore(self, interaction: discord.Interaction):
        db = interaction.client.db
        async with db.execute(
            "SELECT id, titulo, resumo, conteudo FROM lore_entries ORDER BY id ASC"
        ) as cursor:
            entries = await cursor.fetchall()

        if not entries:
            mensagem = "📭 Nenhum lore registrado ainda. Use /lore adicionar ou /lore importar_txt."
            if interaction.response.is_done():
                return await interaction.followup.send(mensagem, ephemeral=True)
            return await interaction.response.send_message(mensagem, ephemeral=True)

        embeds = []
        for entry_id, titulo, resumo, conteudo in entries:
            texto = conteudo or resumo or ""
            partes = _split_text(texto, 3800)
            total = len(partes)
            for index, parte in enumerate(partes, start=1):
                sufixo = f" (parte {index}/{total})" if total > 1 else ""
                embed = discord.Embed(
                    title=f"📚 [{entry_id}] {titulo}{sufixo}",
                    description=parte or "—",
                    color=0x2E7D32,
                )
                embed.set_footer(text="Lore completo registrado pelo mestre.")
                embeds.append(embed)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

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
