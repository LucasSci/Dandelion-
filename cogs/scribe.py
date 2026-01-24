import asyncio
import os
import re
import tempfile
import threading
import wave

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
from data.repositories import DiaryRepository

try:
    from discord.ext import voice_recv
except ImportError:
    voice_recv = None

if voice_recv:
    class TranscriptionSink(voice_recv.AudioSink):
        def __init__(self):
            super().__init__()
            self.audio_data = {}
            self._lock = threading.Lock()
            self.sample_rate = 48000
            self.channels = 2
            self.sample_width = 2

        def wants_opus(self) -> bool:
            return False

        def write(self, user, data):
            if not user:
                return
            if hasattr(data, "sample_rate") and data.sample_rate:
                self.sample_rate = data.sample_rate
            if hasattr(data, "channels") and data.channels:
                self.channels = data.channels
            if hasattr(data, "sample_width") and data.sample_width:
                self.sample_width = data.sample_width
            with self._lock:
                buffer = self.audio_data.setdefault(user.id, bytearray())
                buffer.extend(data.pcm)

        def chunk_size(self, duration_sec: int) -> int:
            return int(self.sample_rate * self.channels * self.sample_width * duration_sec)

        def pop_chunk(self, user_id: int, chunk_size: int) -> bytes | None:
            with self._lock:
                buffer = self.audio_data.get(user_id)
                if not buffer or len(buffer) < chunk_size:
                    return None
                chunk = bytes(buffer[:chunk_size])
                del buffer[:chunk_size]
                return chunk

        def drain_all(self) -> dict[int, bytes]:
            with self._lock:
                drained = {user_id: bytes(audio) for user_id, audio in self.audio_data.items() if audio}
                self.audio_data.clear()
                return drained

        def user_ids(self) -> list[int]:
            with self._lock:
                return list(self.audio_data.keys())

        def cleanup(self) -> None:
            self.audio_data.clear()

# Carrega variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializa cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
DB_NAME = "bestiario.db"

def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

class Scribe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = set() # IDs dos canais que estão sendo gravados
        self.voice_sessions = {} # voice_channel_id -> text_channel_id
        self.voice_summary_channels = {} # voice_channel_id -> summary_channel_id
        self.voice_sinks = {} # voice_channel_id -> sink
        self.voice_tasks = {} # voice_channel_id -> asyncio.Task
        self.voice_transcripts = {} # voice_channel_id -> list[str]
        self._chunk_duration_sec = 2
        self._min_chunk_duration_sec = 0.5
        self.diary_repo = DiaryRepository(bot.db)

    async def _get_transcription_settings(self, guild_id: int) -> tuple[int | None, int | None]:
        async with self.bot.db.execute(
            "SELECT transcription_channel_id, summary_channel_id FROM transcription_settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None, None
        return row[0], row[1]

    async def _set_transcription_settings(
        self,
        guild_id: int,
        transcription_channel_id: int | None,
        summary_channel_id: int | None,
    ) -> None:
        await self.bot.db.execute(
            """
            INSERT INTO transcription_settings (guild_id, transcription_channel_id, summary_channel_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                transcription_channel_id = excluded.transcription_channel_id,
                summary_channel_id = excluded.summary_channel_id
            """,
            (guild_id, transcription_channel_id, summary_channel_id),
        )
        await self.bot.db.commit()

    async def _registrar_mencoes(self, session_log_id: int, content: str) -> None:
        if not content:
            return
        async with self.bot.db.execute("SELECT id, nome FROM personagens WHERE nome IS NOT NULL") as cursor:
            personagens = await cursor.fetchall()
        if not personagens:
            return

        for personagem_id, nome in personagens:
            nome = (nome or "").strip()
            if not nome:
                continue
            pattern = rf"(?<!\w){re.escape(nome)}(?!\w)"
            if re.search(pattern, content, flags=re.IGNORECASE):
                descricao = content if len(content) <= 500 else f"{content[:497]}..."
                await self.diary_repo.add_character_mention(
                    personagem_id=personagem_id,
                    session_log_id=session_log_id,
                    memoria_id=None,
                    descricao_fato=descricao,
                    relevancia=1,
                )

    async def _transcrever_pcm(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 48000,
        channels: int = 2,
        sample_width: int = 2,
    ) -> str | None:
        if not client:
            return None
        if not pcm_bytes:
            return None
        frame_size = channels * sample_width
        if frame_size <= 0:
            return None
        usable_size = len(pcm_bytes) - (len(pcm_bytes) % frame_size)
        if usable_size <= 0:
            return None
        pcm_bytes = pcm_bytes[:usable_size]
        min_bytes = int(sample_rate * channels * sample_width * self._min_chunk_duration_sec)
        if len(pcm_bytes) < min_bytes:
            pcm_bytes = pcm_bytes.ljust(min_bytes, b"\x00")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
            with wave.open(temp_file, "wb") as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)
            temp_file.flush()
            try:
                with open(temp_file.name, "rb") as audio_file:
                    response = await asyncio.to_thread(
                        client.audio.transcriptions.create,
                        model="gpt-4o-mini-transcribe",
                        file=audio_file,
                        language="pt",
                    )
            except Exception:
                return None
        return getattr(response, "text", None)

    async def _resumir_conversa(self, transcricoes: list[str]) -> str | None:
        if not client:
            return None
        if not transcricoes:
            return None

        prompt = (
            "Você é Dandelion, o bardo narrador de The Witcher.\n"
            "Crie um resumo curto e objetivo do que foi conversado na call.\n"
            "Use português brasileiro e destaque decisões importantes, dúvidas ou próximos passos.\n\n"
            "TRANSCRIÇÃO:\n"
            + "\n".join(transcricoes)
        )
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
        except Exception:
            return None
        return response.choices[0].message.content.strip()

    async def _transcription_loop(self, voice_channel_id: int, text_channel_id: int) -> None:
        while voice_channel_id in self.voice_sessions:
            sink = self.voice_sinks.get(voice_channel_id)
            if not sink or not client:
                await asyncio.sleep(1)
                continue

            channel = self.bot.get_channel(text_channel_id)
            voice_channel = self.bot.get_channel(voice_channel_id)
            guild = voice_channel.guild if voice_channel else (channel.guild if channel else None)
            chunk_size = sink.chunk_size(self._chunk_duration_sec)

            for user_id in sink.user_ids():
                chunk = sink.pop_chunk(user_id, chunk_size)
                if not chunk:
                    continue
                texto = await self._transcrever_pcm(
                    chunk,
                    sample_rate=sink.sample_rate,
                    channels=sink.channels,
                    sample_width=sink.sample_width,
                )
                if not texto:
                    continue
                member = guild.get_member(user_id) if guild else None
                nome = member.display_name if member else f"Usuário {user_id}"
                linha = f"{nome}: {texto}"
                self.voice_transcripts.setdefault(voice_channel_id, []).append(linha)
                if channel:
                    await channel.send(f"🎙️ **{nome}:** {texto}")

            await asyncio.sleep(1)

    def _start_transcription_task(self, voice_channel_id: int, text_channel_id: int) -> None:
        existing_task = self.voice_tasks.pop(voice_channel_id, None)
        if existing_task:
            existing_task.cancel()
        self.voice_tasks[voice_channel_id] = asyncio.create_task(
            self._transcription_loop(voice_channel_id, text_channel_id)
        )

    async def _join_voice(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.", ephemeral=True
            )
            return

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "❌ Você precisa estar em uma call para me chamar.", ephemeral=True
            )
            return

        target_channel = voice_state.channel
        voice_client = interaction.guild.voice_client

        bot_member = interaction.guild.me or interaction.guild.get_member(interaction.client.user.id)
        if not bot_member:
            await interaction.response.send_message(
                "❌ Não consegui localizar meu usuário no servidor para validar permissões.",
                ephemeral=True
            )
            return

        permissions = target_channel.permissions_for(bot_member)
        if not permissions.connect or not permissions.speak:
            await interaction.response.send_message(
                "❌ Não tenho permissão para entrar e falar neste canal de voz.",
                ephemeral=True
            )
            return

        if voice_client and voice_client.channel and voice_client.channel.id == target_channel.id:
            await interaction.response.send_message("🔊 Já estou na sua call.", ephemeral=True)
            return

        if voice_recv is None:
            await interaction.response.send_message(
                "❌ Para transcrever a call, instale `discord-ext-voice-recv` e reinicie o bot.",
                ephemeral=True,
            )
            return

        try:
            if voice_client:
                if not hasattr(voice_client, "listen"):
                    await voice_client.disconnect()
                    voice_client = await target_channel.connect(cls=voice_recv.VoiceRecvClient)
                else:
                    await voice_client.move_to(target_channel)
            else:
                voice_client = await target_channel.connect(cls=voice_recv.VoiceRecvClient)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não consegui entrar na call por falta de permissões.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Houve um problema ao entrar na call. Tente novamente.",
                ephemeral=True
            )
            return
        except RuntimeError as exc:
            if "PyNaCl" in str(exc):
                await interaction.response.send_message(
                    "❌ Para usar comandos de voz, instale a biblioteca PyNaCl "
                    "(`pip install pynacl`) e reinicie o bot.",
                    ephemeral=True,
                )
                return
            raise

        sink = TranscriptionSink()
        voice_client.listen(sink)
        self.voice_sinks[target_channel.id] = sink

        transcription_channel_id, summary_channel_id = await self._get_transcription_settings(interaction.guild_id)
        target_transcription_channel_id = transcription_channel_id or interaction.channel_id
        target_summary_channel_id = summary_channel_id or target_transcription_channel_id

        self.voice_sessions[target_channel.id] = target_transcription_channel_id
        self.voice_summary_channels[target_channel.id] = target_summary_channel_id
        self.voice_transcripts[target_channel.id] = []
        self._start_transcription_task(target_channel.id, target_transcription_channel_id)
        await self._log_voice_event(
            target_transcription_channel_id,
            f"EVENTO DA CALL: Dandelion entrou na call **{target_channel.name}**."
        )

        await interaction.response.send_message(
            f"🔊 *Dandelion afina o alaúde e se junta à call* (**{target_channel.name}**)."
        )

    async def _leave_voice(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.", ephemeral=True
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.channel:
            await interaction.response.send_message(
                "❌ Não estou em nenhuma call neste servidor.", ephemeral=True
            )
            return

        voice_channel = voice_client.channel
        text_channel_id = self.voice_sessions.pop(voice_channel.id, None)
        summary_channel_id = self.voice_summary_channels.pop(voice_channel.id, None)
        sink = self.voice_sinks.pop(voice_channel.id, None)
        task = self.voice_tasks.pop(voice_channel.id, None)
        if task:
            task.cancel()
        if sink and hasattr(voice_client, "stop_listening"):
            voice_client.stop_listening()
        await voice_client.disconnect()

        if text_channel_id:
            await self._log_voice_event(
                text_channel_id,
                f"EVENTO DA CALL: Dandelion saiu da call **{voice_channel.name}**."
            )

        await interaction.response.send_message("🔇 *Dandelion fecha o pergaminho da call e sai.*")

        if not sink or not text_channel_id:
            self.voice_transcripts.pop(voice_channel.id, None)
            return
        if not client:
            channel = self.bot.get_channel(text_channel_id)
            if channel:
                await channel.send("⚠️ Não consegui transcrever a call porque a OpenAI não está configurada.")
            self.voice_transcripts.pop(voice_channel.id, None)
            return

        target_summary_channel_id = summary_channel_id or text_channel_id
        channel = self.bot.get_channel(target_summary_channel_id) if target_summary_channel_id else None
        transcricoes = self.voice_transcripts.pop(voice_channel.id, [])
        restante = sink.drain_all()
        for user_id, audio in restante.items():
            texto = await self._transcrever_pcm(
                audio,
                sample_rate=sink.sample_rate,
                channels=sink.channels,
                sample_width=sink.sample_width,
            )
            if texto:
                member = interaction.guild.get_member(user_id) if interaction.guild else None
                nome = member.display_name if member else f"Usuário {user_id}"
                transcricoes.append(f"{nome}: {texto}")
                if channel:
                    await channel.send(f"🎙️ **{nome}:** {texto}")

        if not channel:
            return

        resumo = await self._resumir_conversa(transcricoes)
        if resumo:
            await channel.send(f"📝 **Resumo da call:**\n{resumo}")
        elif transcricoes:
            await channel.send("⚠️ A transcrição foi gerada, mas não consegui resumir o conteúdo.")
        else:
            await channel.send("⚠️ Não consegui capturar áudio suficiente para transcrever.")

    # --- Comandos de Controle ---

    @app_commands.command(name="sessao_iniciar", description="📝 Dandelion começa a ler o chat e anotar o RP.")
    async def sessao_iniciar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            return await interaction.response.send_message("⚠️ Já estou com o pergaminho aberto neste canal!", ephemeral=True)
        
        self.active_sessions.add(interaction.channel_id)
        
        # Opcional: Limpar logs antigos deste canal ao iniciar nova sessão
        async with self.bot.db.execute("DELETE FROM session_logs WHERE channel_id = ?", (interaction.channel_id,)):
            await self.bot.db.commit()

        embed = discord.Embed(
            title="📝 O Escriba está Lendo", 
            description=(
                "*Dandelion puxa um pergaminho novo e afia sua pena.*\n\n"
                "Estou lendo todo o **TEXTO** enviado neste canal (RP e Combates).\n"
                "Ao final, use `/sessao_finalizar` para eu escrever o diário."
            ), 
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sessao_pausar", description="⏸️ Pausa as anotações temporariamente.")
    async def sessao_pausar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            self.active_sessions.remove(interaction.channel_id)
            await interaction.response.send_message("⏸️ *Dandelion para de escrever.* (Leitura pausada)")
        else:
            await interaction.response.send_message("❌ Não estou anotando nada neste canal.", ephemeral=True)

    @app_commands.command(
        name="transcricao_configurar",
        description="🧭 Configura os canais de transcrição e resumo das calls."
    )
    @app_commands.check(is_mestre)
    @app_commands.describe(
        canal_transcricao="Canal de texto para receber a transcrição ao vivo",
        canal_resumo="Canal de texto para receber o resumo da call"
    )
    async def transcricao_configurar(
        self,
        interaction: discord.Interaction,
        canal_transcricao: discord.TextChannel | None = None,
        canal_resumo: discord.TextChannel | None = None,
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )

        existing_transcription_id, existing_summary_id = await self._get_transcription_settings(
            interaction.guild_id
        )
        transcription_channel_id = canal_transcricao.id if canal_transcricao else existing_transcription_id
        summary_channel_id = canal_resumo.id if canal_resumo else existing_summary_id

        if not transcription_channel_id and not summary_channel_id:
            return await interaction.response.send_message(
                "❌ Informe ao menos um canal para transcrição ou resumo.",
                ephemeral=True,
            )

        if not transcription_channel_id:
            transcription_channel_id = summary_channel_id
        if not summary_channel_id:
            summary_channel_id = transcription_channel_id

        await self._set_transcription_settings(
            interaction.guild_id,
            transcription_channel_id,
            summary_channel_id,
        )

        resumo_canal = self.bot.get_channel(summary_channel_id)
        transcricao_canal = self.bot.get_channel(transcription_channel_id)
        await interaction.response.send_message(
            "✅ Canais configurados!\n"
            f"🎙️ **Transcrição:** {transcricao_canal.mention if transcricao_canal else f'<#{transcription_channel_id}>'}\n"
            f"📝 **Resumo:** {resumo_canal.mention if resumo_canal else f'<#{summary_channel_id}>'}",
            ephemeral=True,
        )

    @app_commands.command(name="call_entrar", description="🔊 (Mestre) Dandelion entra na call e registra os eventos.")
    @app_commands.check(is_mestre)
    async def call_entrar(self, interaction: discord.Interaction):
        await self._join_voice(interaction)

    @app_commands.command(
        name="voz_entrar",
        description="🔊 (Mestre) Dandelion entra na call para registrar a conversa."
    )
    @app_commands.check(is_mestre)
    async def voz_entrar(self, interaction: discord.Interaction):
        await self._join_voice(interaction)

    @app_commands.command(name="call_sair", description="🔇 (Mestre) Dandelion sai da call e encerra os registros.")
    @app_commands.check(is_mestre)
    async def call_sair(self, interaction: discord.Interaction):
        await self._leave_voice(interaction)

    @app_commands.command(
        name="voz_sair",
        description="🔇 (Mestre) Dandelion sai da call e encerra os registros."
    )
    @app_commands.check(is_mestre)
    async def voz_sair(self, interaction: discord.Interaction):
        await self._leave_voice(interaction)

    @app_commands.command(name="sessao_finalizar", description="📕 Encerra a sessão e escreve o Diário.")
    async def sessao_finalizar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            self.active_sessions.remove(interaction.channel_id)

        await interaction.response.defer()

        # 1. Resgatar o Log do Banco de Dados
        # CORREÇÃO: Adicionado 'as cursor' que faltava no código anterior
        async with self.bot.db.execute("SELECT user_name, content, is_bot FROM session_logs WHERE channel_id = ? ORDER BY id ASC", (interaction.channel_id,)) as cursor:
            logs = await cursor.fetchall()

        if not logs:
            return await interaction.followup.send("📜 A folha está em branco. Nada foi escrito no chat durante a sessão.")

        # 2. Formatar para a IA ler
        texto_bruto = ""
        for nome, conteudo, is_bot in logs:
            prefixo = "[SISTEMA]" if is_bot else f"[{nome}]"
            texto_bruto += f"{prefixo}: {conteudo}\n"

        # 3. Gerar o Resumo com OpenAI (GPT-4o)
        if not client:
            return await interaction.followup.send("❌ API Key da OpenAI não configurada no arquivo .env")

        system_prompt = """
        Você é Dandelion, o bardo poeta de The Witcher.
        Sua tarefa é escrever um DIÁRIO NARRATIVO resumindo a sessão de RPG baseada nos logs de chat fornecidos.
        
        Diretrizes:
        - O texto fornecido é o histórico do CHAT de texto.
        - Ignore comandos técnicos (/rolar, etc), erros ou mensagens de sistema irrelevantes.
        - Interprete os resultados numéricos (ex: '25 dano') transformando-os em narrativa de ação.
        - Exalte os feitos dos jogadores e dramatize as falhas.
        - Mantenha um tom poético, exagerado e carismático.
        - Escreva em Português.
        """

        # Limite de segurança para não estourar o contexto (aprox 15k caracteres finais)
        user_message = f"Aqui está o registro do chat da aventura:\n\n{texto_bruto[-15000:]}"

        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            diario_completo = response.choices[0].message.content or ""

            # Cortar se for muito longo para o Discord (limite de 4096 caracteres na descrição do Embed)
            diario_exibicao = diario_completo
            if len(diario_exibicao) > 4000:
                diario_exibicao = diario_exibicao[:4000] + "... (continua no próximo bardo)"

            cursor = await self.bot.db.execute(
                "INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Resumo', ?)",
                (diario_completo,),
            )
            await self.bot.db.commit()
            sessao_id = cursor.lastrowid

            async with self.bot.db.execute("SELECT id, nome FROM personagens") as personagem_cursor:
                personagens = await personagem_cursor.fetchall()

            diario_lower = diario_completo.lower()
            for personagem_id, nome in personagens:
                nome_normalizado = (nome or "").strip().lower()
                if nome_normalizado and nome_normalizado in diario_lower:
                    await self.bot.db.execute(
                        """
                        INSERT OR IGNORE INTO personagem_memorias (personagem_id, sessao_id)
                        VALUES (?, ?)
                        """,
                        (personagem_id, sessao_id),
                    )
            await self.bot.db.commit()

            embed = discord.Embed(
                title="📕 As Crônicas da Sessão",
                description=diario_exibicao,
                color=0x7A0000,
            )
            embed.set_footer(text="Escrito por Dandelion (via OpenAI)")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ A pena quebrou (Erro na API): {str(e)}")

    # --- O Ouvinte (Listener de Texto) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora se não estiver gravando este canal
        if message.channel.id not in self.active_sessions: return
        # Ignora comandos para não poluir o log
        if message.content.startswith("/"): return

        content = message.content
        is_bot = message.author.bot
        user_name = message.author.display_name

        # Captura conteúdo rico de Embeds (ex: resultados de combate do bot Dandelion)
        if is_bot and message.embeds:
            embed = message.embeds[0]
            desc = embed.description if embed.description else ""
            title = embed.title if embed.title else ""
            # Formata campos do embed (ex: Dano: 20) numa linha só
            fields = " | ".join([f"{f.name}: {f.value}" for f in embed.fields])
            content = f"EVENTO DO SISTEMA: {title} - {desc} {fields}"
        
        # Se não tiver texto nenhum (só imagem sem descrição), ignora
        if not content: return

        # Salva no Banco de Dados
        try:
            cursor = await self.bot.db.execute(
                "INSERT INTO session_logs (channel_id, user_name, content, is_bot) VALUES (?, ?, ?, ?)",
                (message.channel.id, user_name, content, is_bot)
            )
            await self.bot.db.commit()
            if cursor.lastrowid:
                await self._registrar_mencoes(cursor.lastrowid, content)
        except Exception as e:
            print(f"Erro ao salvar log: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_client = member.guild.voice_client if member.guild else None
        if not voice_client or not voice_client.channel:
            return

        monitored_channel_id = voice_client.channel.id
        text_channel_id = self.voice_sessions.get(monitored_channel_id)
        if not text_channel_id:
            return

        events = []
        if before.channel != after.channel:
            if after.channel and after.channel.id == monitored_channel_id:
                events.append(f"EVENTO DA CALL: {member.display_name} entrou na call.")
            elif before.channel and before.channel.id == monitored_channel_id:
                events.append(f"EVENTO DA CALL: {member.display_name} saiu da call.")

        if before.self_mute != after.self_mute:
            estado = "mutou o microfone" if after.self_mute else "tirou o mute do microfone"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")
        if before.mute != after.mute:
            estado = "foi silenciado" if after.mute else "teve o silêncio removido"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")
        if before.self_deaf != after.self_deaf:
            estado = "ativou o surdo" if after.self_deaf else "desativou o surdo"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")
        if before.deaf != after.deaf:
            estado = "foi ensurdecido" if after.deaf else "teve a audição liberada"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")
        if before.self_stream != after.self_stream:
            estado = "começou a transmitir a tela" if after.self_stream else "parou de transmitir a tela"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")
        if before.self_video != after.self_video:
            estado = "ligou a câmera" if after.self_video else "desligou a câmera"
            events.append(f"EVENTO DA CALL: {member.display_name} {estado}.")

        for event in events:
            await self._log_voice_event(text_channel_id, event)

    async def _log_voice_event(self, channel_id: int, content: str) -> None:
        try:
            await self.bot.db.execute(
                "INSERT INTO session_logs (channel_id, user_name, content, is_bot) VALUES (?, ?, ?, ?)",
                (channel_id, "Sistema", content, True)
            )
            await self.bot.db.commit()
        except Exception as e:
            print(f"Erro ao salvar evento da call: {e}")

async def setup(bot):
    await bot.add_cog(Scribe(bot))
