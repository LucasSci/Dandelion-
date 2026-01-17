import discord
from discord import ui
from utils import rolar_dados

# --- MODAL PARA CRIAR NOVA HABILIDADE ---
class NovaHabilidadeModal(ui.Modal, title="✨ Nova Habilidade"):
    def __init__(self, personagem_id, view_pai):
        super().__init__()
        self.personagem_id = personagem_id
        self.view_pai = view_pai

    nome = ui.TextInput(label="Nome da Habilidade", placeholder="Ex: Bola de Fogo")
    # Mantido required=False pois o placeholder indica opcionalidade
    dado = ui.TextInput(label="Dano/Efeito (Dados)", placeholder="Ex: 4d6 (Deixe vazio se não tiver)", required=False)
    # Added placeholder for better UX
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

        # FIX: Usando a conexão compartilhada do bot via interaction.client
        db = interaction.client.db
        
        await db.execute("""
            INSERT INTO habilidades_personagem (personagem_id, nome, descricao, dado)
            VALUES (?, ?, ?, ?)
        """, (self.personagem_id, self.nome.value, self.descricao.value, self.dado.value))
        await db.commit()
        
        await interaction.response.send_message(f"✅ Habilidade **{self.nome.value}** aprendida!", ephemeral=True)
        await self.view_pai.atualizar_botoes_habilidade(interaction)

# --- BOTÃO DE HABILIDADE (REALIZA A ROLAGEM) ---
class HabilidadeButton(ui.Button):
    def __init__(self, nome, dado, descricao):
        label_btn = f"{nome} ({dado})" if dado else nome

        # UX Improvement: Visual distinction for skill types
        if dado:
            style = discord.ButtonStyle.primary
            emoji = "🎲"
        else:
            style = discord.ButtonStyle.secondary
            emoji = "✨"
        # Improved UX: Visual distinction between active (rollable) and passive skills
        if dado:
            emoji = "🎲"
            style = discord.ButtonStyle.primary
            label_btn = f"{nome} [{dado}]"
        else:
            emoji = "✨"
            style = discord.ButtonStyle.secondary
            label_btn = nome

        super().__init__(style=style, label=label_btn, emoji=emoji, row=1)
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

# --- VIEW PRINCIPAL DA FICHA ---
class FichaView(ui.View):
    def __init__(self, personagem_id, user_id_dono):
        super().__init__(timeout=None)
        self.personagem_id = personagem_id
        self.dono_id = user_id_dono
        self.update_buttons_state("info")

    def update_buttons_state(self, mode: str):
        """Atualiza estado dos botões de navegação (visual feedback)"""
        for item in self.children:
            if isinstance(item, ui.Button) and item.label:
                if item.label == "📜 Info/Lore":
                    item.disabled = (mode == "info")
                elif item.label == "⚔️ Habilidades":
                    item.disabled = (mode == "skills")

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
        await interaction.response.send_modal(NovaHabilidadeModal(self.personagem_id, self))

    # --- MÉTODOS DE EXIBIÇÃO ---
    
    async def mostrar_info_geral(self, interaction: discord.Interaction):
        self.update_buttons_state("info")
        
        # FIX: Usando connection pool compartilhado
        db = interaction.client.db
        
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
        
        self.clear_dynamic_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def atualizar_botoes_habilidade(self, interaction: discord.Interaction):
        self.update_buttons_state("skills")
        self.clear_dynamic_buttons()

        # FIX: Usando connection pool compartilhado
        db = interaction.client.db

        async with db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (self.personagem_id,)) as cursor:
            skills = await cursor.fetchall()

        embed = discord.Embed(title="⚔️ Grimório de Habilidades", color=0x992d22)
        if not skills:
            embed.description = "Nenhuma habilidade aprendida. Clique em '➕ Nova Skill'."
        else:
            embed.description = "Clique nos botões abaixo para usar:"

        for nome, dado, desc in skills[:20]:
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