import discord
from discord import ui

# --- VISUAL: BARRA DE VIDA ---
def gerar_barra(atual, maximo, tamanho=10):
    if maximo <= 0:
        pct = 0
    else:
        pct = max(0, min(atual / maximo, 1))

    cheios = int(pct * tamanho)

    # Define a cor com base na porcentagem de vida
    if pct > 0.6:
        cor = "🟩"  # Alta (Verde)
    elif pct > 0.3:
        cor = "🟨"  # Média (Amarelo)
    else:
        cor = "🟥"  # Baixa/Crítica (Vermelho)

    return cor * cheios + "⬛" * (tamanho - cheios)

# --- LINK EXTERNO (ROLL20) ---
class Roll20LinkView(ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(
            ui.Button(
                label="Abrir no Roll20",
                emoji="🎲",
                style=discord.ButtonStyle.link,
                url=url,
            )
        )

# --- VIEW DO MESTRE (TRAVA DE NARRATIVA) ---
class MestreView(ui.View):
    def __init__(self, cog, channel_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id

    @ui.button(label="Destravar / Próximo Turno", emoji="▶️", style=discord.ButtonStyle.success)
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
        if jogador_atual['tipo'] == 'MONSTRO':
            await interaction.response.send_message("⏳ Aguarde o turno do inimigo.", ephemeral=True)
            return False

        if interaction.user.id != jogador_atual['user_id']:
            await interaction.response.send_message(f"⏳ Espere sua vez! Agora é o turno de **{jogador_atual['nome']}**.", ephemeral=True)
            return False

        return True

    @ui.button(label="Atacar", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def btn_atacar(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Ataque Básico")

    @ui.button(label="Defender", emoji="🛡️", style=discord.ButtonStyle.secondary)
    async def btn_defender(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Defesa")
