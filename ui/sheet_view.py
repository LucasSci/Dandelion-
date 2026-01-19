import discord
from discord import ui
from utils import rolar_dados
from ui.views import ConfirmarExclusaoView

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

        db = interaction.client.db
        
        await db.execute("""
            INSERT INTO habilidades_personagem (personagem_id, nome, descricao, dado)
            VALUES (?, ?, ?, ?)
        """, (self.personagem_id, self.nome.value, self.descricao.value, self.dado.value))
        await db.commit()
        
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

        db = interaction.client.db
        await db.execute("""
            UPDATE habilidades_personagem 
            SET nome=?, dado=?, descricao=? 
            WHERE id=?
        """, (self.nome_input.value, self.dado_input.value, self.desc_input.value, self.skill_id))
        await db.commit()
        
        await interaction.response.send_message(f"✅ Habilidade **{self.nome_input.value}** atualizada!", ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

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

    @ui.button(label="✏️ Editar", style=discord.ButtonStyle.primary)
    async def btn_editar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(
            EditarHabilidadeModal(self.skill_id, self.nome, self.dado, self.desc, self.view_ficha)
        )

    @ui.button(label="🗑️ Excluir", style=discord.ButtonStyle.danger)
    async def btn_excluir(self, interaction: discord.Interaction, button: ui.Button):
        async def confirmar(itx: discord.Interaction):
            db = itx.client.db
            await db.execute("DELETE FROM habilidades_personagem WHERE id = ?", (self.skill_id,))
            await db.commit()

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
            
            options.append(discord.SelectOption(
                label=nome[:100], 
                value=str(id_skill), 
                description=desc_curta[:100],
                emoji="🔸"
            ))

        super().__init__(placeholder="Selecione uma habilidade...", min_values=1, max_values=1, options=options)
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

# ==============================================================================
# 3. COMPONENTES DA FICHA PRINCIPAL
# ==============================================================================

class HabilidadeButton(ui.Button):
    def __init__(self, nome, dado, descricao):
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

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ {interaction.user.display_name} usou {self.nome_habilidade}", color=0xFF5500)
        embed.description = self.desc_habilidade or "..."
        
        if self.dado_habilidade:
            detalhes, total = rolar_dados(self.dado_habilidade)
            if detalhes:
                embed.add_field(name="🎲 Rolagem", value=f"`{self.dado_habilidade}`\nResult: {detalhes}\n# **{total}**")
        
        await interaction.response.send_message(embed=embed)

class FichaView(ui.View):
    def __init__(self, personagem_id, user_id_dono):
        super().__init__(timeout=None)
        self.personagem_id = personagem_id
        self.dono_id = user_id_dono
        self.update_buttons_state("info")

    def update_buttons_state(self, mode: str):
        for item in self.children:
            if isinstance(item, ui.Button) and item.label:
                if item.label == "Info/Lore":
                    is_active = (mode == "info")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary
                elif item.label == "Habilidades":
                    is_active = (mode == "skills")
                    item.disabled = is_active
                    item.style = discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # ============================================================
        # ALTERAÇÃO: Permite Dono OU Administrador (Mestre)
        # ============================================================
        is_dono = interaction.user.id == self.dono_id
        is_mestre = interaction.user.guild_permissions.administrator

        if is_dono or is_mestre:
            return True
            
        await interaction.response.send_message("⛔ Esta ficha não é sua.", ephemeral=True)
        return False

    # --- NAVEGAÇÃO (ROW 0) ---
    @ui.button(label="Info/Lore", emoji="📜", style=discord.ButtonStyle.secondary, row=0)
    async def btn_info(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_info_geral(interaction)

    @ui.button(label="Habilidades", emoji="⚔️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_skills(self, interaction: discord.Interaction, button: ui.Button):
        await self.atualizar_botoes_habilidade(interaction)

    @ui.button(label="Nova Skill", emoji="➕", style=discord.ButtonStyle.success, row=0)
    async def btn_add_skill(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(NovaHabilidadeModal(self.personagem_id, self))

    @ui.button(label="Gerenciar", emoji="⚙️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_gerenciar(self, interaction: discord.Interaction, button: ui.Button):
        db = interaction.client.db
        async with db.execute("SELECT id, nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (self.personagem_id,)) as cursor:
            skills = await cursor.fetchall()

        if not skills:
            return await interaction.response.send_message("❌ Você não tem habilidades para gerenciar.", ephemeral=True)

        view_gerenciar = GerenciarHabilidadesView(skills, self)
        await interaction.response.send_message("Selecione a habilidade que deseja editar ou excluir:", view=view_gerenciar, ephemeral=True)

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        self.update_buttons_state("info")
        
        db = interaction.client.db
        async with db.execute("SELECT nome, raca, classe, nivel, historia, imagem_url, ouro, hp_atual, hp_max FROM personagens WHERE id = ?", (self.personagem_id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados: return
        nome, raca, classe, nivel, historia, img, ouro, hp_atual, hp_max = dados
        if hp_atual is None: hp_atual = hp_max

        embed = discord.Embed(title=f"📜 {nome}", description=historia or "Sem registro.", color=0x2b2d31)
        embed.add_field(name="Raça", value=raca, inline=True)
        embed.add_field(name="Classe", value=classe, inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        
        barra = "🟩" * int((hp_atual/hp_max)*10) if hp_max > 0 else "🟩"*10
        embed.add_field(name="❤️ Vida", value=f"{hp_atual}/{hp_max}\n`{barra}`", inline=True)
        
        embed.add_field(name="Ouro", value=f"💰 {ouro}", inline=True)
        if img: embed.set_thumbnail(url=img)
        
        self.clear_dynamic_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_botoes_habilidade(self, interaction: discord.Interaction):
        self.update_buttons_state("skills")
        self.clear_dynamic_buttons()

        db = interaction.client.db
        async with db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ? LIMIT 20", (self.personagem_id,)) as cursor:
            skills = await cursor.fetchall()

        embed = discord.Embed(title="⚔️ Grimório de Habilidades", color=0x992d22)
        if not skills:
            embed.description = "Nenhuma habilidade aprendida. Clique em '➕ Nova Skill'."
        else:
            embed.description = "Clique para usar ou '⚙️ Gerenciar' para editar:"

        for nome, dado, desc in skills:
            self.add_item(HabilidadeButton(nome, dado, desc))

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    def clear_dynamic_buttons(self):
        items_to_keep = [item for item in self.children if getattr(item, 'row', 0) == 0]
        self.clear_items()
        for item in items_to_keep:
            self.add_item(item)