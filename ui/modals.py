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
                title = f"✨ Personagem Criado: {self.nome.value}"
                footer_text = "Use /ficha para ver os detalhes completos."
                desc = "Sua jornada começa agora!"
            else:
                title = f"📂 Personagem Arquivado: {self.nome.value}"
                footer_text = "Arquivado no Pool do Mestre. Use /mestre_vincular para atribuir."
                desc = "Personagem pronto para ser atribuído."

            embed = discord.Embed(
                title=title,
                description=desc,
                color=0x57F287  # Green
            )

            # Identity Field
            raca = self.raca.value or "Desconhecida"
            classe = self.classe.value or "Aventureiro"
            embed.add_field(name="Identidade", value=f"**{raca}** • *{classe}*", inline=True)

            # History Field (if provided)
            if self.historia.value:
                historia_curta = (self.historia.value[:200] + '...') if len(self.historia.value) > 200 else self.historia.value
                embed.add_field(name="História", value=f"_{historia_curta}_", inline=False)

            # Thumbnail (if provided)
            if self.imagem.value:
                embed.set_thumbnail(url=self.imagem.value)

            embed.set_footer(text=footer_text)
            
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
