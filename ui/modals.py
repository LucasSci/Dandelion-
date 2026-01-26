import discord
from discord import ui

# DB_NAME não é mais necessário aqui

class CriarFichaModal(ui.Modal, title="⚔️ Registro de Personagem"):
    def __init__(self, target_user_id=None):
        super().__init__()
        self.target_user_id = target_user_id

    nome = ui.TextInput(label="Nome do Personagem", placeholder="Ex: Geralt de Rívia")
    raca = ui.TextInput(label="Raça", placeholder="Ex: Bruxo, Humano, Elfo")
    classe = ui.TextInput(label="Classe", placeholder="Ex: Guerreiro, Mago")
    
    # Conformidade verificada: required=False em campos opcionais
    historia = ui.TextInput(
        label="Breve História",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
        placeholder="Ex: Um caçador de monstros em busca..."
    )
    # Added placeholder for better UX
    imagem = ui.TextInput(label="URL da Imagem (Avatar)", required=False, placeholder="Ex: https://imgur.com/avatar.png")

    async def on_submit(self, interaction: discord.Interaction):
        final_user_id = self.target_user_id

        if final_user_id == 'proprio':
            final_user_id = interaction.user.id
        
        # FIX: Acessando DB via client, evitando abrir nova conexão (bolt.md)
        db = interaction.client.db

        try:
            # Não usamos 'async with db' aqui, pois a conexão é persistente. 
            # Usamos apenas o execute.
            await db.execute("""
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
            await db.commit()

            if final_user_id:
                title = "✨ Personagem Criado!"
                desc = f"A jornada de **{self.nome.value}** começa agora."
                color = 0x57F287  # Green
                footer = "Use /ficha para acessar seu painel."
            else:
                title = "📂 Personagem Arquivado"
                desc = f"**{self.nome.value}** foi salvo no Pool de Fichas do Mestre."
                color = 0x95A5A6  # Grey
                footer = "Use /mestre_vincular para atribuir a alguém."

            embed = discord.Embed(title=title, description=desc, color=color)
            embed.add_field(name="Raça", value=self.raca.value, inline=True)
            embed.add_field(name="Classe", value=self.classe.value, inline=True)

            if self.imagem.value:
                embed.set_thumbnail(url=self.imagem.value)

            embed.set_footer(text=footer)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            # Capturando IntegrityError genericamente ou checando o tipo de erro específico do aiosqlite/sqlite3
            if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(type(e)):
                 await interaction.response.send_message(
                    f"❌ O nome **{self.nome.value}** já existe! Por favor, escolha outro.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)
