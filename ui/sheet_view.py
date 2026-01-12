import discord
import aiosqlite
import random
import re
from discord import ui
from utils import rolar_dados
DB_NAME = "bestiario.db"

# --- MODAL PARA CRIAR NOVA HABILIDADE ---
class NovaHabilidadeModal(ui.Modal, title="✨ Nova Habilidade"):
    def __init__(self, personagem_id, view_pai, message: discord.Message):
        super().__init__()
        self.personagem_id = personagem_id
        self.view_pai = view_pai
        self.message = message

    nome = ui.TextInput(label="Nome da Habilidade", placeholder="Ex: Bola de Fogo")
    dado = ui.TextInput(label="Dano/Efeito (Dados)", placeholder="Ex: 4d6 (Deixe vazio se não tiver)")
    descricao = ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Valida fórmula de dado se preenchida
        if self.dado.value and not re.match(r'(\d+)d(\d+)', self.dado.value.lower()):
            return await interaction.response.send_message("❌ Fórmula de dados inválida. Use ex: 1d20+5", ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT INTO habilidades_personagem (personagem_id, nome, descricao, dado)
                VALUES (?, ?, ?, ?)
            """, (self.personagem_id, self.nome.value, self.descricao.value, self.dado.value))
            await db.commit()
        
        await interaction.response.send_message(f"✅ Habilidade **{self.nome.value}** aprendida!", ephemeral=True)
        # Atualiza a mensagem original da ficha
        await self.view_pai.update_message(self.message)

# --- BOTÃO DE HABILIDADE (REALIZA A ROLAGEM) ---
class HabilidadeButton(ui.Button):
    def __init__(self, nome, dado, descricao):
        label_btn = f"{nome} ({dado})" if dado else nome
        super().__init__(style=discord.ButtonStyle.secondary, label=label_btn, row=1)
        self.nome_habilidade = nome
        self.dado_habilidade = dado
        self.desc_habilidade = descricao

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ Usou {self.nome_habilidade}", color=0xFF5500)
        embed.description = self.desc_habilidade or "..."
        
        if self.dado_habilidade:
            detalhes, total = rolar_dados(self.dado_habilidade)
            if detalhes:
                embed.add_field(name="🎲 Rolagem", value=f"`{self.dado_habilidade}`\nResult: {detalhes}\n# **{total}**")
        
        await interaction.response.send_message(embed=embed)

# --- VIEW PRINCIPAL DA FICHA ---
class FichaView(ui.View):
    def __init__(self, personagem_id, user_id_dono):
        super().__init__(timeout=None)
        self.personagem_id = personagem_id
        self.dono_id = user_id_dono

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("⛔ Esta ficha não é sua.", ephemeral=True)
            return False
        return True

    # --- NAVEGAÇÃO ---
    @ui.button(label="📜 Info/Lore", style=discord.ButtonStyle.primary, row=0)
    async def btn_info(self, interaction: discord.Interaction, button: ui.Button):
        await self.mostrar_info_geral(interaction)

    @ui.button(label="⚔️ Habilidades", style=discord.ButtonStyle.success, row=0)
    async def btn_skills(self, interaction: discord.Interaction, button: ui.Button):
        await self.atualizar_botoes_habilidade(interaction)

    @ui.button(label="➕ Nova Skill", style=discord.ButtonStyle.gray, row=0)
    async def btn_add_skill(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(NovaHabilidadeModal(self.personagem_id, self, interaction.message))

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        # Busca dados atualizados do banco
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT nome, raca, classe, nivel, historia, imagem_url, ouro FROM personagens WHERE id = ?", (self.personagem_id,)) as cursor:
                dados = await cursor.fetchone()
        
        if not dados: return
        nome, raca, classe, nivel, historia, img, ouro = dados

        embed = discord.Embed(title=f"📜 {nome}", description=historia or "Sem registro.", color=0x2b2d31)
        embed.add_field(name="Raça", value=raca, inline=True)
        embed.add_field(name="Classe", value=classe, inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="Ouro", value=f"💰 {ouro}", inline=True)
        if img: embed.set_thumbnail(url=img)
        
        # Limpa botões de habilidade (row 1+) para limpar a tela
        self.clear_dynamic_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _update_view_with_skills(self):
        # 1. Limpa botões antigos de habilidade
        self.clear_dynamic_buttons()

        # 2. Busca habilidades do banco
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (self.personagem_id,)) as cursor:
                skills = await cursor.fetchall()

        # 3. Cria Embed
        embed = discord.Embed(title="⚔️ Grimório de Habilidades", color=0x992d22)
        if not skills:
            embed.description = "Nenhuma habilidade aprendida. Clique em '➕ Nova Skill'."
        else:
            embed.description = "Clique nos botões abaixo para usar:"

        # 4. Adiciona um botão para cada habilidade (Max 20 por limite do Discord)
        for nome, dado, desc in skills[:20]:
            self.add_item(HabilidadeButton(nome, dado, desc))

        return embed

    async def atualizar_botoes_habilidade(self, interaction: discord.Interaction):
        embed = await self._update_view_with_skills()

        # Se a interação já foi respondida (ex: vindo do Modal), usamos edit_original_response
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def update_message(self, message: discord.Message):
        embed = await self._update_view_with_skills()
        await message.edit(embed=embed, view=self)

    def clear_dynamic_buttons(self):
        # Remove todos os itens que não sejam os botões fixos de navegação (Info, Skills, Add)
        # Itens fixos estão na row 0. Dinâmicos na row 1.
        items_to_keep = [item for item in self.children if getattr(item, 'row', 0) == 0]
        self.clear_items()
        for item in items_to_keep:
            self.add_item(item)