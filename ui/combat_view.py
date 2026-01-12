import discord
from discord import ui
import random

# --- VISUAL: BARRA DE VIDA ---
def gerar_barra(atual, maximo, tamanho=10):
    pct = max(0, atual / maximo)
    cheios = int(pct * tamanho)
    return "🟩" * cheios + "⬛" * (tamanho - cheios)

class CombateView(ui.View):
    def __init__(self, combate_cog, combate_id):
        super().__init__(timeout=None)
        self.cog = combate_cog
        self.combate_id = combate_id

    # --- CONTROLE DE ACESSO ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        session = self.cog.sessions.get(self.combate_id)
        if not session:
            await interaction.response.send_message("❌ Combate encerrado.", ephemeral=True)
            return False
            
        # Verifica se é a vez de quem clicou
        jogador_atual = session['ordem'][session['turno_index']]
        
        # Se for turno do monstro, ninguém clica (o bot processa sozinho)
        if session['turno_monstro']:
            await interaction.response.send_message("🚫 É a vez do monstro! Aguarde.", ephemeral=True)
            return False

        # Verifica ID do jogador
        if interaction.user.id != jogador_atual['user_id']:
            await interaction.response.send_message(f"⏳ Espere sua vez! Agora é o turno de **{jogador_atual['nome']}**.", ephemeral=True)
            return False

        return True

    # --- AÇÕES ---
    @ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.danger)
    async def btn_atacar(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Ataque Básico")

    @ui.button(label="🛡️ Defender", style=discord.ButtonStyle.secondary)
    async def btn_defender(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Defesa")
    
    @ui.button(label="✨ Habilidade", style=discord.ButtonStyle.primary)
    async def btn_skill(self, interaction: discord.Interaction, button: ui.Button):
        # Aqui você poderia abrir um Modal ou SelectMenu com as skills do banco
        # Por simplificação, faremos um ataque forte
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Habilidade Especial")