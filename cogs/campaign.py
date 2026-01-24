import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from data.repositories import DiaryRepository
from data_cache import (
    clear_world_location_caches,
    get_world_location_details,
    get_world_location_names,
)
from data.repositories import CharacterMentionRepository, CharacterRepository

class Campaign(commands.Cog):
    diario_campanha = app_commands.Group(
        name="diario_campanha", description="Comandos do diário da campanha."
    )
    lore = app_commands.Group(name="lore", description="Comandos de lore do mundo.")
    mundo = app_commands.Group(name="mundo", description="Comandos de mundo, bioma e ambientação.")

    def __init__(self, bot):
        self.bot = bot
        self.character_repo = CharacterRepository(bot.db)
        self.character_mention_repo = CharacterMentionRepository(bot.db)

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

    async def localizacao_autocomplete(self, interaction: discord.Interaction, current: str):
        nomes = await get_world_location_names(self.bot.db)
        termo = current.strip().lower()
        if termo:
            nomes = [nome for nome in nomes if termo in nome.lower()]
        return [app_commands.Choice(name=nome, value=nome) for nome in nomes[:25]]

    @diario_campanha.command(
        name="ver", description="📖 Vê a Linha do Tempo atual da campanha (O que a IA sabe)"
    )
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

    @diario_campanha.command(name="adicionar", description="➕ Adiciona um evento HOJE na linha do tempo")
    @diario.command(name="personagem", description="📓 Mostra os últimos fatos do seu personagem")
    @app_commands.describe(usuario="Outro jogador (apenas mestre)")
    async def diario_personagem(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None,
    ):
        if usuario and not is_mestre(interaction):
            return await interaction.response.send_message(
                "❌ Apenas o Mestre pode consultar o diário de outros jogadores.",
                ephemeral=True,
            )

        target = usuario or interaction.user
        personagem = await self.character_repo.fetch_character_summary_by_user(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, _, _ = personagem
        mencoes = await self.character_mention_repo.list_mentions(personagem_id, limit=5)

        if mencoes:
            descricao = "\n".join(
                f"**[{m_id}]** {fato} (relevância: {relevancia}, {criado_em})"
                for m_id, fato, relevancia, criado_em, _ in mencoes
            )
            embed = discord.Embed(
                title=f"📓 Diário de {personagem_nome}",
                description=descricao,
                color=0x8D6E63,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        async with self.bot.db.execute(
            """
            SELECT id, conteudo, data_registro
            FROM memoria_campanha
            ORDER BY id DESC
            LIMIT 5
            """
        ) as cursor:
            memoria = await cursor.fetchall()

        if not memoria:
            return await interaction.response.send_message(
                "📭 Nenhum fato registrado ainda para a campanha.",
                ephemeral=True,
            )

        descricao = "\n".join(
            f"**[{mem_id}]** {conteudo} ({data_registro})"
            for mem_id, conteudo, data_registro in memoria
        )
        embed = discord.Embed(
            title="📖 Últimos fatos da campanha",
            description=descricao,
            color=0x8D6E63,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @diario.command(name="adicionar", description="➕ Adiciona um evento HOJE na linha do tempo")
    @app_commands.describe(evento="Ex: 'O grupo chegou em Zerrikania e irritou o sultão.'")
    @app_commands.check(is_mestre)
    async def add_evento(self, interaction: discord.Interaction, evento: str):
        await self.bot.db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Evento', ?)", (evento,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"✅ Evento registrado no fim da fila.", ephemeral=True)

    @diario_campanha.command(
        name="consequencia", description="➕ Registra consequência persistente de uma ação"
    )
    @app_commands.describe(consequencia="Ex: 'A vila agora teme bruxos e recusa abrigo.'")
    @app_commands.check(is_mestre)
    async def add_consequencia(self, interaction: discord.Interaction, consequencia: str):
        await self.bot.db.execute(
            "INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Consequence', ?)",
            (consequencia,),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Consequência registrada.", ephemeral=True)

    @diario_campanha.command(
        name="importar_txt", description="📂 Importa um resumo longo via arquivo .txt"
    )
    @app_commands.check(is_mestre)
    async def import_txt(self, interaction: discord.Interaction, arquivo: discord.Attachment):
        if not arquivo.filename.endswith('.txt'): return await interaction.response.send_message("Apenas .txt", ephemeral=True)
        await interaction.response.defer()
        
        texto = (await arquivo.read()).decode('utf-8')
        # Divide o texto em blocos menores se for muito grande, ou salva como 'Resumo'
        await self.bot.db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Resumo', ?)", (texto,))
        await self.bot.db.commit()
        
        await interaction.followup.send(f"✅ Resumo importado! A IA agora conhece esse contexto.")

    @diario_campanha.command(name="editar", description="✏️ Corrige um evento errado na memória")
    @app_commands.describe(id_evento="Número do ID (veja no /diario ver)", novo_texto="O texto correto")
    @app_commands.check(is_mestre)
    async def edit_evento(self, interaction: discord.Interaction, id_evento: int, novo_texto: str):
        cursor = await self.bot.db.execute("UPDATE memoria_campanha SET conteudo = ? WHERE id = ?", (novo_texto, id_evento))
        await self.bot.db.commit()
        
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Evento [{id_evento}] atualizado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ID não encontrado.", ephemeral=True)

    @diario_campanha.command(name="apagar", description="🗑️ Remove um evento da memória")
    @app_commands.check(is_mestre)
    async def del_evento(self, interaction: discord.Interaction, id_evento: int):
        await self.bot.db.execute("DELETE FROM memoria_campanha WHERE id = ?", (id_evento,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"🗑️ Evento [{id_evento}] removido da linha do tempo.", ephemeral=True)

    @diario_campanha.command(name="limpar_tudo", description="⚠️ APAGA TODA A MEMÓRIA (Reset)")
    @app_commands.check(is_mestre)
    async def wipe_memory(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM memoria_campanha")
        await self.bot.db.commit()
        await interaction.response.send_message("🔥 **TABULA RASA!** O Dandelion esqueceu tudo sobre a campanha.", ephemeral=True)

    @lore.command(name="ver", description="📚 Vê o conhecimento de mundo registrado pelo mestre")
    async def lore_ver(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator
        query = "SELECT id, titulo, resumo, conteudo FROM lore_entries"
        params = []
        if not is_admin:
            query += " WHERE (is_private = 0 OR is_private IS NULL OR owner_id = ?)"
            params.append(interaction.user.id)
        query += " ORDER BY id ASC"

        is_mestre = Campaign.is_mestre(interaction)
        params = []
        query = "SELECT id, titulo, resumo, conteudo FROM lore_entries"
        if not is_mestre:
            query += " WHERE is_private = 0 OR is_private IS NULL OR owner_id = ?"
            params.append(interaction.user.id)
        query += " ORDER BY id ASC"
        async with self.bot.db.execute(query, params) as c:
            rows = await c.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "📭 Nenhum lore registrado ainda. Use /lore adicionar ou /lore importar_txt.",
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

    @lore.command(name="adicionar", description="➕ Registra um fato do mundo para a IA usar")
    @app_commands.describe(
        titulo="Título curto do lore",
        conteudo="Texto completo do conhecimento",
        is_private="Marque como privado para limitar a visualização",
        owner_id="ID do jogador dono do lore (opcional)",
    )
    @app_commands.check(is_mestre)
    async def lore_adicionar(
        self,
        interaction: discord.Interaction,
        titulo: str,
        conteudo: str,
        is_private: bool = False,
        owner_id: Optional[int] = None,
    ):
        resumo = self._resumir_texto(conteudo, 240)
        if is_private and owner_id is None:
            owner_id = interaction.user.id
        await self.bot.db.execute(
            "INSERT INTO lore_entries (titulo, resumo, conteudo, is_private, owner_id) VALUES (?, ?, ?, ?, ?)",
            (titulo, resumo, conteudo, int(is_private), owner_id),
        )
        await self.bot.db.commit()
        await interaction.response.send_message("✅ Lore registrado com sucesso.", ephemeral=True)

    @lore.command(name="importar_txt", description="📂 Importa lore longo via arquivo .txt")
    @app_commands.describe(
        titulo="Título do lore",
        arquivo="Arquivo .txt com o conteúdo",
        is_private="Marque como privado para limitar a visualização",
        owner_id="ID do jogador dono do lore (opcional)",
    )
    @app_commands.check(is_mestre)
    async def lore_importar_txt(
        self,
        interaction: discord.Interaction,
        titulo: str,
        arquivo: discord.Attachment,
        is_private: bool = False,
        owner_id: Optional[int] = None,
    ):
        if not arquivo.filename.endswith(".txt"):
            return await interaction.response.send_message("Apenas .txt", ephemeral=True)
        await interaction.response.defer()

        texto = (await arquivo.read()).decode("utf-8")
        resumo = self._resumir_texto(texto, 240)
        if is_private and owner_id is None:
            owner_id = interaction.user.id
        await self.bot.db.execute(
            "INSERT INTO lore_entries (titulo, resumo, conteudo, is_private, owner_id) VALUES (?, ?, ?, ?, ?)",
            (titulo, resumo, texto, int(is_private), owner_id),
        )
        await self.bot.db.commit()
        await interaction.followup.send("✅ Lore importado! A IA agora conhece esse conteúdo.")

    @lore.command(name="editar", description="✏️ Corrige um lore existente")
    @app_commands.describe(
        id_lore="ID do lore (veja em /lore ver)",
        novo_titulo="Novo título",
        novo_conteudo="Novo texto",
        is_private="Atualiza se o lore é privado",
        owner_id="ID do jogador dono do lore (opcional)",
    )
    @app_commands.check(is_mestre)
    async def lore_editar(
        self,
        interaction: discord.Interaction,
        id_lore: int,
        novo_titulo: str,
        novo_conteudo: str,
        is_private: Optional[bool] = None,
        owner_id: Optional[int] = None,
    ):
        resumo = self._resumir_texto(novo_conteudo, 240)
        fields = [
            "titulo = ?",
            "resumo = ?",
            "conteudo = ?",
            "atualizado_em = datetime('now')",
        ]
        params = [novo_titulo, resumo, novo_conteudo]
        if is_private is not None:
            fields.append("is_private = ?")
            params.append(int(is_private))
            if is_private is False and owner_id is None:
                fields.append("owner_id = NULL")
        resolved_owner_id = owner_id
        if is_private is True and resolved_owner_id is None:
            resolved_owner_id = interaction.user.id
        if resolved_owner_id is not None:
            fields.append("owner_id = ?")
            params.append(resolved_owner_id)
        params.append(id_lore)
        query = f"UPDATE lore_entries SET {', '.join(fields)} WHERE id = ?"
        cursor = await self.bot.db.execute(query, params)
        await self.bot.db.commit()

        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Lore [{id_lore}] atualizado.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ID não encontrado.", ephemeral=True)

    @lore.command(name="apagar", description="🗑️ Remove um lore do banco de conhecimento")
    @app_commands.check(is_mestre)
    async def lore_apagar(self, interaction: discord.Interaction, id_lore: int):
        await self.bot.db.execute("DELETE FROM lore_entries WHERE id = ?", (id_lore,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"🗑️ Lore [{id_lore}] removido.", ephemeral=True)

    @lore.command(name="limpar_tudo", description="⚠️ Apaga TODO o banco de conhecimento do mundo")
    @app_commands.check(is_mestre)
    async def lore_limpar_tudo(self, interaction: discord.Interaction):
        await self.bot.db.execute("DELETE FROM lore_entries")
        await self.bot.db.commit()
        await interaction.response.send_message("🔥 Todo o lore foi apagado.", ephemeral=True)

    @mundo.command(name="definir_bioma", description="🔒 Define bioma e clima de uma região.")
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
            clear_world_location_caches()
            await interaction.response.send_message(
                f"✅ {local} atualizado para **{biome}** / **{clima}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Localização não encontrada.", ephemeral=True)

    @mundo.command(name="ambientacao", description="🌦️ Gera ambientação por bioma/clima.")
    @app_commands.describe(local="Nome da localização", foco="Foco opcional (ex: tensão, mistério)")
    @app_commands.autocomplete(local=localizacao_autocomplete)
    async def ambientacao_gerar(
        self,
        interaction: discord.Interaction,
        local: str,
        foco: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)

        row = await get_world_location_details(self.bot.db, local)

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
