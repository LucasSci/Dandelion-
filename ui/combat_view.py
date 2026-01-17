import discord
from discord import ui

# --- VISUAL: BARRA DE VIDA ---
def gerar_barra(atual, maximo, tamanho=10):
    pct = max(0, atual / maximo)
    cheios = int(pct * tamanho)
    return "🟩" * cheios + "⬛" * (tamanho - cheios)

# --- VIEW DO MESTRE (TRAVA DE NARRATIVA) ---
class MestreView(ui.View):
    def __init__(self, cog, channel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id

    @ui.button(label="▶️ Destravar / Próximo Turno", style=discord.ButtonStyle.success)
    async def btn_proximo(self, interaction: discord.Interaction, button: ui.Button):
        # Verifica se é admin/mestre (pode ajustar a permissão conforme necessidade)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Apenas o Mestre pode avançar a cena!", ephemeral=True)
        
        await self.cog.destravar_turno(interaction, self.channel_id)

# --- SELEÇÃO DE SKILLS (Mantida) ---
class SkillSelect(ui.Select):
    def __init__(self, habilidades, cog, combate_id):
        options = []
        for nome, dado, desc in habilidades:
            label = f"{nome}"
            desc_curta = f"Dano/Efeito: {dado}" if dado else "Efeito sem dano"
            value_str = f"{nome}|{dado}"
            emoji = "🎲" if dado else "✨"
            options.append(discord.SelectOption(label=label, description=desc_curta, value=value_str, emoji=emoji))

        super().__init__(placeholder="✨ Escolha uma habilidade...", min_values=1, max_values=1, options=options)
        self.cog = cog
        self.combate_id = combate_id

    async def callback(self, interaction: discord.Interaction):
        selecao = self.values[0]
        nome_skill, formula = selecao.split("|")
        await self.cog.processar_acao_jogador(
            interaction, 
            self.combate_id, 
            acao="Habilidade", 
            detalhes_skill={"nome": nome_skill, "formula": formula}
        )

# --- VIEW DO JOGADOR (COMBATE) ---
class CombateView(ui.View):
    def __init__(self, combate_cog, combate_id, habilidades_jogador=None):
        super().__init__(timeout=None)
        self.cog = combate_cog
        self.combate_id = combate_id
        
        if habilidades_jogador:
            self.add_item(SkillSelect(habilidades_jogador, combate_cog, combate_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        session = self.cog.sessions.get(self.combate_id)
        if not session:
            await interaction.response.send_message("❌ Combate encerrado.", ephemeral=True)
            return False
            
        # Se estiver travado pelo mestre, ninguém clica nesta View (embora ela deva sumir)
        if session.get('bloqueado', False):
            await interaction.response.send_message("✋ O Mestre está narrando a cena. Aguarde!", ephemeral=True)
            return False

        jogador_atual = session['ordem'][session['turno_index']]
        if interaction.user.id != jogador_atual['user_id']:
            await interaction.response.send_message(f"⏳ Espere sua vez! Agora é o turno de **{jogador_atual['nome']}**.", ephemeral=True)
            return False

        return True

    @ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.danger)
    async def btn_atacar(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Ataque Básico")

    @ui.button(label="🛡️ Defender", style=discord.ButtonStyle.secondary)
    async def btn_defender(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Defesa")