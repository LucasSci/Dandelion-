import discord
from discord import ui

class ConfirmarExclusaoView(ui.View):
    def __init__(self, confirm_callback, cancel_callback=None):
        super().__init__(timeout=60)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback

    @ui.button(label="Confirmar Exclusão", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        # Desativa os botões para evitar duplo clique
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        try:
            await self.confirm_callback(interaction)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao processar: {e}", ephemeral=True)
        self.stop()

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        if self.cancel_callback:
            await self.cancel_callback(interaction)
        else:
            # Padrão: Edita a mensagem removendo a view e avisando que foi cancelado
            await interaction.response.edit_message(content="❌ Ação cancelada.", view=None)
        self.stop()
