import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

class Campaign(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_mestre(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="diario_ver", description="📖 Vê a Linha do Tempo atual da campanha (O que a IA sabe)")
    @app_commands.check(is_mestre)
    async def ver_diario(self, interaction: discord.Interaction):
        # Busca tudo ordenado por ID (Ordem de inserção = Ordem Cronológica)
        async with self.bot.db.execute("SELECT id, conteudo FROM memoria_campanha WHERE tipo IN ('Evento', 'Resumo', 'Quest') ORDER BY id ASC") as c:
            rows = await c.fetchall()
        
        if not rows:
            return await interaction.response.send_message("📭 O diário está vazio. A IA não sabe nada sobre sua história atual.", ephemeral=True)

        # Monta um texto legível
        texto = ""
        for r in rows:
            # Limita tamanho para não estourar mensagem
            conteudo = r[1][:150] + "..." if len(r[1]) > 150 else r[1]
            texto += f"**[{r[0]}]** {conteudo}\n"

        embed = discord.Embed(title="📖 Diário do Dandelion (Timeline)", description=texto, color=0xA84300)
        embed.set_footer(text="A IA usará APENAS estes fatos para gerar missões.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="diario_adicionar", description="➕ Adiciona um evento HOJE na linha do tempo")
    @app_commands.describe(evento="Ex: 'O grupo chegou em Zerrikania e irritou o sultão.'")
    @app_commands.check(is_mestre)
    async def add_evento(self, interaction: discord.Interaction, evento: str):
        await self.bot.db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Evento', ?)", (evento,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"✅ Evento registrado no fim da fila.", ephemeral=True)

    @app_commands.command(name="diario_importar_txt", description="📂 Importa um resumo longo via arquivo .txt")
    @app_commands.check(is_mestre)
    async def import_txt(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        if not arquivo.filename.endswith('.txt'): return await interaction.response.send_message("Apenas .txt", ephemeral=True)
        await interaction.response.defer()
        
        texto = (await arquivo.read()).decode('utf-8')
        # Divide o texto em blocos menores se for muito grande, ou salva como 'Resumo'
        await self.bot.db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Resumo', ?)", (texto,))
        await self.bot.db.commit()
        
        await interaction.followup.send(f"✅ Resumo importado! A IA agora conhece esse contexto.")

    @app_commands.command(name="diario_editar", description="✏️ Corrige um evento errado na memória")
    @app_commands.describe(id_evento="Número do ID (veja no /diario_ver)", novo_texto="O texto correto")
    @app_commands.check(is_mestre)
    async def edit_evento(self, interaction: discord.Interaction, id_evento: int, novo_texto: str):
        cursor = await self.bot.db.execute("UPDATE memoria_campanha SET conteudo = ? WHERE id = ?", (novo_texto, id_evento))
        await self.bot.db.commit()
        
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Evento [{id_evento}] atualizado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ID não encontrado.", ephemeral=True)

    @app_commands.command(name="diario_apagar", description="🗑️ Remove um evento da memória")
    @app_commands.check(is_mestre)
    async def del_evento(self, interaction: discord.Interaction, id_evento: int):
        await self.bot.db.execute("DELETE FROM memoria_campanha WHERE id = ?", (id_evento,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"🗑️ Evento [{id_evento}] removido da linha do tempo.", ephemeral=True)

    @app_commands.command(name="diario_limpar_tudo", description="⚠️ APAGA TODA A MEMÓRIA (Reset)")
    @app_commands.check(is_mestre)
    async def wipe_memory(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM memoria_campanha")
        await self.bot.db.commit()
        await interaction.response.send_message("🔥 **TABULA RASA!** O Dandelion esqueceu tudo sobre a campanha.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Campaign(bot))