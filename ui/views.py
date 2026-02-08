import discord
from discord import ui

from utils.i18n import resolve_locale, translate

class ConfirmarExclusaoView(ui.View):
    def __init__(self, confirm_callback, cancel_callback=None, locale: str | None = None):
        super().__init__(timeout=60)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self.locale = resolve_locale(locale)
        self._apply_labels()

    def _apply_labels(self) -> None:
        labels = [
            translate("ui.confirm_delete.confirm_label", locale=self.locale),
            translate("ui.confirm_delete.cancel_label", locale=self.locale),
        ]
        for index, child in enumerate(self.children):
            if isinstance(child, ui.Button) and index < len(labels):
                child.label = labels[index]

    @ui.button(label="Confirmar Exclusão", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        # Desativa os botões para evitar duplo clique
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        try:
            await self.confirm_callback(interaction)
        except Exception as e:
            await interaction.followup.send(
                translate("ui.confirm_delete.error", locale=self.locale, error=e),
                ephemeral=True,
            )
        self.stop()

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        if self.cancel_callback:
            await self.cancel_callback(interaction)
        else:
            # Padrão: Edita a mensagem removendo a view e avisando que foi cancelado
            await interaction.response.edit_message(
                content=translate("ui.confirm_delete.cancelled", locale=self.locale),
                view=None,
            )
        self.stop()
