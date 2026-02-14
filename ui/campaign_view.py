import discord
from discord import ui
from data.repositories.lore_repository import LoreRepository

class AddEventModal(ui.Modal, title="Adicionar Evento na Linha do Tempo"):
    conteudo = ui.TextInput(
        label="Descrição do Evento",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: O grupo derrotou o Grifo Real em Valen.",
        max_length=2000,
        required=True
    )

    def __init__(self, repo: LoreRepository):
        super().__init__()
        self.repo = repo

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            row_id = await self.repo.add_event(self.conteudo.value)
            await interaction.followup.send(f"✅ Evento #{row_id} registrado!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class AddLoreModal(ui.Modal, title="Adicionar Conhecimento (Lore)"):
    titulo = ui.TextInput(label="Título", placeholder="Ex: História de Novigrad", max_length=100)
    regiao = ui.TextInput(label="Região (Opcional)", placeholder="Global, Velen, Skellige...", required=False, default="Global")
    conteudo = ui.TextInput(
        label="Conteúdo",
        style=discord.TextStyle.paragraph,
        placeholder="Texto completo sobre o assunto...",
        max_length=3000,
        required=True
    )

    def __init__(self, repo: LoreRepository):
        super().__init__()
        self.repo = repo

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            reg = self.regiao.value.strip() or "Global"
            row_id = await self.repo.add_lore(
                titulo=self.titulo.value,
                conteudo=self.conteudo.value,
                regiao=reg,
                is_private=False, # Default public via modal
                owner_id=interaction.user.id
            )
            await interaction.followup.send(f"✅ Lore '{self.titulo.value}' adicionado em **{reg}**!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)


class CampaignManagerView(ui.View):
    def __init__(self, db, user_id: int):
        super().__init__(timeout=600)
        self.repo = LoreRepository(db)
        self.user_id = user_id
        self.current_mode = "timeline" # or "lore"
        self.lore_region_filter = "Global"

    async def _check_permission(self, interaction: discord.Interaction) -> bool:
        # Apenas mestre ou quem abriu (se for mestre)
        allowed = False
        if interaction.user.id == self.user_id:
            allowed = True
        elif interaction.user.guild_permissions.administrator:
            allowed = True

        if not allowed:
            await interaction.response.send_message("⛔ Você não tem permissão para usar este painel.", ephemeral=True)
            return False
        return True

    async def update_embed(self, interaction: discord.Interaction):
        is_mestre = interaction.user.guild_permissions.administrator

        embed = discord.Embed(color=0x2B2D31)

        if self.current_mode == "timeline":
            events = await self.repo.get_recent_events(limit=10)
            embed.title = "📜 Linha do Tempo (Últimos 10)"
            desc = ""
            if not events:
                desc = "*Nenhum evento registrado.*"
            else:
                for eid, tipo, conteudo, data in events:
                    # data format YYYY-MM-DD HH:MM:SS
                    dt = data.split()[0] if data else "?"
                    desc += f"**[{eid}]** `{dt}` {conteudo[:100]}\n"
            embed.description = desc
            embed.set_footer(text="Use 'Add Evento' para registrar fatos.")

        elif self.current_mode == "lore":
            lore_items = await self.repo.get_lore(
                regiao=self.lore_region_filter,
                limit=10,
                is_mestre=is_mestre,
                user_id=interaction.user.id
            )
            embed.title = f"📚 Biblioteca de Lore: {self.lore_region_filter}"

            if not lore_items:
                embed.description = "*Nenhum conhecimento encontrado nesta região.*"
            else:
                for lid, tit, res, cont, reg in lore_items:
                    embed.add_field(
                        name=f"[{lid}] {tit} ({reg})",
                        value=res or "*Sem resumo*",
                        inline=False
                    )
            embed.set_footer(text="Filtre por região nos botões abaixo.")

        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="📜 Timeline", style=discord.ButtonStyle.primary, row=0)
    async def btn_timeline(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check_permission(interaction): return
        self.current_mode = "timeline"
        await self.update_embed(interaction)

    @ui.button(label="➕ Add Evento", style=discord.ButtonStyle.success, row=0)
    async def btn_add_event(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check_permission(interaction): return
        await interaction.response.send_modal(AddEventModal(self.repo))

    @ui.button(label="📚 Lore (Global)", style=discord.ButtonStyle.secondary, row=1)
    async def btn_lore_global(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check_permission(interaction): return
        self.current_mode = "lore"
        self.lore_region_filter = "Global"
        await self.update_embed(interaction)

    @ui.button(label="➕ Add Lore", style=discord.ButtonStyle.success, row=1)
    async def btn_add_lore(self, interaction: discord.Interaction, button: ui.Button):
        if not await self._check_permission(interaction): return
        await interaction.response.send_modal(AddLoreModal(self.repo))
