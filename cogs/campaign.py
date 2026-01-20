import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from typing import Optional

class Campaign(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _resumir_texto(texto: str, limite: int = 200) -> str:
        texto = (texto or "").strip()
        if len(texto) <= limite:
            return texto
        return f"{texto[:limite]}..."

    def is_mestre(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    async def localizacao_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute(
            "SELECT nome FROM world_locations WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    @app_commands.command(name="diario_ver", description="📖 Vê a Linha do Tempo atual da campanha (O que a IA sabe)")
    @app_commands.check(is_mestre)
    async def ver_diario(self, interaction: discord.Interaction):
        # Busca tudo ordenado por ID (Ordem de inserção = Ordem Cronológica)
        async with self.bot.db.execute(
            "SELECT id, conteudo FROM memoria_campanha WHERE tipo IN ('Evento', 'Resumo', 'Quest', 'Consequence') ORDER BY id ASC"
        ) as c:
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

    @app_commands.command(name="diario_consequencia", description="➕ Registra consequência persistente de uma ação")
    @app_commands.describe(consequencia="Ex: 'A vila agora teme bruxos e recusa abrigo.'")
    @app_commands.check(is_mestre)
    async def add_consequencia(self, interaction: discord.Interaction, consequencia: str):
        await self.bot.db.execute(
            "INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Consequence', ?)",
            (consequencia,),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Consequência registrada.", ephemeral=True)

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

        texto = ""
        for entry_id, titulo, resumo, conteudo in rows:
            base = resumo or conteudo or ""
            base = self._resumir_texto(base, 150)
            texto += f"**[{entry_id}]** {titulo}: {base}\n"

        embed = discord.Embed(title="📚 Banco de Conhecimento do Mundo", description=texto, color=0x2E7D32)
        embed.set_footer(text="A IA usa este lore como verdade adicional para criar missões.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    @app_commands.command(name="localizacao_definir_bioma", description="🔒 Define bioma e clima de uma região.")
    @app_commands.describe(local="Nome da localização", biome="Bioma principal", clima="Clima dominante")
    @app_commands.autocomplete(local=localizacao_autocomplete)
    @app_commands.check(is_mestre)
    async def localizacao_definir_bioma(
        self, interaction: discord.Interaction, local: str, biome: str, clima: str
    ):
        cursor = await self.bot.db.execute(
            "UPDATE world_locations SET biome = ?, clima = ? WHERE nome = ?",
            (biome, clima, local),
        )
        await self.bot.db.commit()

        if cursor.rowcount > 0:
            await interaction.response.send_message(
                f"✅ {local} atualizado para **{biome}** / **{clima}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Localização não encontrada.", ephemeral=True)

    @app_commands.command(name="ambientacao_gerar", description="🌦️ Gera ambientação por bioma/clima.")
    @app_commands.describe(local="Nome da localização", foco="Foco opcional (ex: tensão, mistério)")
    @app_commands.autocomplete(local=localizacao_autocomplete)
    async def ambientacao_gerar(
        self,
        interaction: discord.Interaction,
        local: str,
        foco: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        async with self.bot.db.execute(
            "SELECT descricao, biome, clima FROM world_locations WHERE nome = ?",
            (local,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.followup.send("❌ Localização não encontrada.")

        descricao, biome, clima = row
        ai = self.bot.get_cog("AIHandler")
        if not ai:
            return await interaction.followup.send("❌ IA indisponível.")

        prompt = (
            "Crie uma ambientação curta para RPG de fantasia.\n"
            f"Local: {local}\n"
            f"Descrição: {descricao or 'Sem descrição'}\n"
            f"Bioma: {biome or 'Não definido'}\n"
            f"Clima: {clima or 'Não definido'}\n"
            f"Foco: {foco or 'geral'}\n"
            "Retorne 3 a 5 frases com detalhes sensoriais."
        )

        texto = await ai.get_response(prompt)
        embed = discord.Embed(
            title=f"🌦️ Ambientação: {local}",
            description=texto,
            color=0x3498DB,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Campaign(bot))
