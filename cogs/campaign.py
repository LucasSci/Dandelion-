import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

class Campaign(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _split_text(texto: str, limite: int = 3900) -> list[str]:
        texto = (texto or "").strip()
        if not texto:
            return [""]
        return [texto[i : i + limite] for i in range(0, len(texto), limite)]

    @staticmethod
    def _resumir_texto(texto: str, limite: int = 200) -> str:
        texto = (texto or "").strip()
        if len(texto) <= limite:
            return texto
        return f"{texto[:limite]}..."

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

    @app_commands.command(name="lore_ver", description="📚 Vê o conhecimento de mundo registrado pelo mestre")
    @app_commands.check(is_mestre)
    async def lore_ver(self, interaction: discord.Interaction):
        async with self.bot.db.execute(
            "SELECT id, titulo, resumo, conteudo FROM lore_entries ORDER BY id ASC"
        ) as c:
            rows = await c.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhum lore registrado ainda. Use /lore_adicionar ou /lore_importar_txt.",
                ephemeral=True,
            )

        embeds = []
        for entry_id, titulo, resumo, conteudo in rows:
            partes = self._split_text(conteudo or resumo or "", 3900)
            total = len(partes)
            for index, parte in enumerate(partes, start=1):
                sufixo = f" (parte {index}/{total})" if total > 1 else ""
                embed = discord.Embed(
                    title=f"📚 [{entry_id}] {titulo}{sufixo}",
                    description=parte or "—",
                    color=0x2E7D32,
                )
                embed.set_footer(text="A IA usa este lore como verdade adicional para criar missões.")
                embeds.append(embed)

        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        for embed in embeds[1:]:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="lore_adicionar", description="➕ Registra um fato do mundo para a IA usar")
    @app_commands.describe(titulo="Título curto do lore", conteudo="Texto completo do conhecimento")
    @app_commands.check(is_mestre)
    async def lore_adicionar(self, interaction: discord.Interaction, titulo: str, conteudo: str):
        resumo = self._resumir_texto(conteudo, 240)
        await self.bot.db.execute(
            "INSERT INTO lore_entries (titulo, resumo, conteudo) VALUES (?, ?, ?)",
            (titulo, resumo, conteudo),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Lore registrado com sucesso.", ephemeral=True)

    @app_commands.command(name="lore_importar_txt", description="📂 Importa lore longo via arquivo .txt")
    @app_commands.describe(titulo="Título do lore", arquivo="Arquivo .txt com o conteúdo")
    @app_commands.check(is_mestre)
    async def lore_importar_txt(self, interaction: discord.Interaction, titulo: str, arquivo: discord.Attachment):
        if not arquivo.filename.endswith(".txt"):
            return await interaction.response.send_message("Apenas .txt", ephemeral=True)
        await interaction.response.defer()

        texto = (await arquivo.read()).decode("utf-8")
        resumo = self._resumir_texto(texto, 240)
        await self.bot.db.execute(
            "INSERT INTO lore_entries (titulo, resumo, conteudo) VALUES (?, ?, ?)",
            (titulo, resumo, texto),
        )
        await self.bot.db.commit()
        await interaction.followup.send("✅ Lore importado! A IA agora conhece esse conteúdo.")

    @app_commands.command(name="lore_editar", description="✏️ Corrige um lore existente")
    @app_commands.describe(id_lore="ID do lore (veja em /lore_ver)", novo_titulo="Novo título", novo_conteudo="Novo texto")
    @app_commands.check(is_mestre)
    async def lore_editar(
        self,
        interaction: discord.Interaction,
        id_lore: int,
        novo_titulo: str,
        novo_conteudo: str,
    ):
        resumo = self._resumir_texto(novo_conteudo, 240)
        cursor = await self.bot.db.execute(
            "UPDATE lore_entries SET titulo = ?, resumo = ?, conteudo = ?, atualizado_em = datetime('now') WHERE id = ?",
            (novo_titulo, resumo, novo_conteudo, id_lore),
        )
        await self.bot.db.commit()

        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Lore [{id_lore}] atualizado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ID não encontrado.", ephemeral=True)

    @app_commands.command(name="lore_apagar", description="🗑️ Remove um lore do banco de conhecimento")
    @app_commands.check(is_mestre)
    async def lore_apagar(self, interaction: discord.Interaction, id_lore: int):
        await self.bot.db.execute("DELETE FROM lore_entries WHERE id = ?", (id_lore,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"🗑️ Lore [{id_lore}] removido.", ephemeral=True)

    @app_commands.command(name="lore_limpar_tudo", description="⚠️ Apaga TODO o banco de conhecimento do mundo")
    @app_commands.check(is_mestre)
    async def lore_limpar_tudo(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM lore_entries")
        await self.bot.db.commit()
        await interaction.response.send_message("🔥 Todo o lore foi apagado.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Campaign(bot))
