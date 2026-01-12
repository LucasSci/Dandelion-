import aiosqlite
import discord
from discord import ui

DB_NAME = "bestiario.db"

class CriarFichaModal(ui.Modal, title="⚔️ Registro de Personagem"):
    def __init__(self, target_user_id=None):
        super().__init__()
        # Se target_user_id for None, a ficha é criada "sem dono" (Pool do Mestre)
        # Se for preenchido com ID, já nasce vinculada
        self.target_user_id = target_user_id

    nome = ui.TextInput(label="Nome do Personagem", placeholder="Ex: Geralt de Rívia")
    raca = ui.TextInput(label="Raça", placeholder="Ex: Bruxo, Humano, Elfo")
    classe = ui.TextInput(label="Classe", placeholder="Ex: Guerreiro, Mago")
    historia = ui.TextInput(
        label="Breve História",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    imagem = ui.TextInput(label="URL da Imagem (Avatar)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Define quem será o dono inicial
        final_user_id = self.target_user_id

        # Se self.target_user_id for 'proprio' (definido no comando), usa o ID de quem digitou
        if final_user_id == 'proprio':
            final_user_id = interaction.user.id
        
        try:
            async with aiosqlite.connect(DB_NAME) as conn:
                await conn.execute("""
                    INSERT INTO personagens
                    (user_id, nome, raca, classe, historia, imagem_url, ouro)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (
                    final_user_id,
                    self.nome.value.strip(),
                    self.raca.value,
                    self.classe.value,
                    self.historia.value,
                    self.imagem.value
                ))
                await conn.commit()

            # Feedback personalizado
            if final_user_id:
                msg = f"✅ **{self.nome.value}** nasceu! Use `/ficha` para ver."
            else:
                msg = f"📂 **{self.nome.value}** foi arquivado no Pool de Fichas do Mestre.\nUse `/mestre_vincular` para entregar a alguém."
            
            await interaction.response.send_message(msg, ephemeral=True)

        except aiosqlite.IntegrityError:
            await interaction.response.send_message(
                f"❌ O nome **{self.nome.value}** já existe! Por favor, escolha outro.",
                ephemeral=True
            )