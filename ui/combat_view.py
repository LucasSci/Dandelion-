import discord
from discord import ui
from utils import gerar_barra
from utils.i18n import resolve_locale, translate

# --- LINK EXTERNO (ROLL20) ---
class Roll20LinkView(ui.View):
    def __init__(self, url: str, locale: str | None = None):
        super().__init__(timeout=None)
        locale = resolve_locale(locale)
        self.add_item(
            ui.Button(
                label=translate("ui.combat.roll20_open", locale=locale),
                emoji="🎲",
                style=discord.ButtonStyle.link,
                url=url,
            )
        )

# --- VIEW DO MESTRE (TRAVA DE NARRATIVA) ---
class MestreView(ui.View):
    def __init__(self, cog, channel_id, locale: str | None = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.locale = resolve_locale(locale)
        self._apply_labels()

    def _apply_labels(self) -> None:
        for child in self.children:
            if isinstance(child, ui.Button) and child.callback.__name__ == "btn_proximo":
                child.label = translate("ui.combat.unlock_turn", locale=self.locale)

    @ui.button(label="Destravar / Próximo Turno", emoji="▶️", style=discord.ButtonStyle.success)
    async def btn_proximo(self, interaction: discord.Interaction, button: ui.Button):
        # Verifica se é admin/mestre (pode ajustar a permissão conforme necessidade)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                translate("ui.combat.only_master", locale=self.locale),
                ephemeral=True,
            )
        
        await self.cog.destravar_turno(interaction, self.channel_id)

# --- SELEÇÃO DE SKILLS (Mantida) ---
class SkillSelect(ui.Select):
    def __init__(self, habilidades, cog, combate_id, locale: str | None = None):
        self.locale = resolve_locale(locale)
        options = []
        for nome, dado, desc in habilidades:
            label = f"{nome}"
            desc_curta = (
                translate("ui.combat.skill_damage", locale=self.locale, value=dado)
                if dado
                else translate("ui.combat.skill_no_damage", locale=self.locale)
            )
            value_str = f"{nome}|{dado}"
            emoji = "🎲" if dado else "✨"
            options.append(discord.SelectOption(label=label, description=desc_curta, value=value_str, emoji=emoji))

        super().__init__(
            placeholder=translate("ui.combat.skill_placeholder", locale=self.locale),
            min_values=1,
            max_values=1,
            options=options,
        )
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
    def __init__(self, combate_cog, combate_id, habilidades_jogador=None, locale: str | None = None):
        super().__init__(timeout=None)
        self.cog = combate_cog
        self.combate_id = combate_id
        self.locale = resolve_locale(locale)
        self._apply_labels()
        
        if habilidades_jogador:
            self.add_item(SkillSelect(habilidades_jogador, combate_cog, combate_id, locale=self.locale))

    def _apply_labels(self) -> None:
        for child in self.children:
            if not isinstance(child, ui.Button):
                continue
            if child.callback.__name__ == "btn_atacar":
                child.label = translate("ui.combat.attack", locale=self.locale)
            elif child.callback.__name__ == "btn_defender":
                child.label = translate("ui.combat.defend", locale=self.locale)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        session = self.cog.sessions.get(self.combate_id)
        if not session:
            await interaction.response.send_message(
                translate("ui.combat.session_ended", locale=self.locale),
                ephemeral=True,
            )
            return False
            
        # Se estiver travado pelo mestre, ninguém clica nesta View (embora ela deva sumir)
        if session.get('bloqueado', False):
            await interaction.response.send_message(
                translate("ui.combat.locked", locale=self.locale),
                ephemeral=True,
            )
            return False

        jogador_atual = session['ordem'][session['turno_index']]
        if jogador_atual['tipo'] == 'MONSTRO':
            await interaction.response.send_message(
                translate("ui.combat.wait_enemy", locale=self.locale),
                ephemeral=True,
            )
            return False

        if interaction.user.id != jogador_atual['user_id']:
            await interaction.response.send_message(
                translate("ui.combat.wait_turn", locale=self.locale, name=jogador_atual["nome"]),
                ephemeral=True,
            )
            return False

        return True

    @ui.button(label="Atacar", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def btn_atacar(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Ataque Básico")

    @ui.button(label="Defender", emoji="🛡️", style=discord.ButtonStyle.secondary)
    async def btn_defender(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.processar_acao_jogador(interaction, self.combate_id, "Defesa")
