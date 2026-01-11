import aiosqlite
import discord
from discord import ui

DB_NAME = "bestiario.db"

class CriarFichaModal(ui.Modal, title="⚔️ Registro de Personagem"):
    nome = ui.TextInput(label="Nome")
    raca = ui.TextInput(label="Raça")
    classe = ui.TextInput(label="Classe")
    historia = ui.TextInput(
        label="História",
        style=discord.TextStyle.paragraph,
        required=False
    )
    imagem = ui.TextInput(label="URL da Imagem", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Conexão assíncrona
        async with aiosqlite.connect(DB_NAME) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO personagens
                (user_id, nome, raca, classe, historia, imagem_url, ouro)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                interaction.user.id,
                self.nome.value.title(),
                self.raca.value,
                self.classe.value,
                self.historia.value,
                self.imagem.value
            ))
            await conn.commit()

        await interaction.response.send_message(
            "✨ Ficha registrada com sucesso!",
            ephemeral=True
        )