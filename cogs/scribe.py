import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
from openai import OpenAI
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Carrega variáveis
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class Scribe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = set()

    # --- Comandos de Controle ---

    @app_commands.command(name="sessao_iniciar", description="📝 Dandelion começa a ler o chat.")
    async def sessao_iniciar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            return await interaction.response.send_message("⚠️ Já estou com o pergaminho aberto neste canal!", ephemeral=True)
        
        self.active_sessions.add(interaction.channel_id)
        
        # Limpar logs antigos deste canal
        async with self.bot.db.execute("DELETE FROM session_logs WHERE channel_id = ?", (interaction.channel_id,)):
            await self.bot.db.commit()

        embed = discord.Embed(
            title="📝 O Escriba está Lendo", 
            description=(
                "*Dandelion puxa um pergaminho novo e afia sua pena.*\n\n"
                "Estou lendo todo o **TEXTO** enviado neste canal.\n"
                "Ao final, use `/sessao_finalizar` para eu escrever o diário."
            ), 
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sessao_pausar", description="⏸️ Pausa as anotações temporariamente.")
    async def sessao_pausar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            self.active_sessions.remove(interaction.channel_id)
            await interaction.response.send_message("⏸️ *Dandelion para de escrever.* (Pausado)")
        else:
            await interaction.response.send_message("❌ Não estou anotando nada aqui.", ephemeral=True)

    @app_commands.command(name="sessao_finalizar", description="📕 Encerra a sessão e escreve o Diário (IA).")
    async def sessao_finalizar(self, interaction: discord.Interaction):
        if interaction.channel_id in self.active_sessions:
            self.active_sessions.remove(interaction.channel_id)

        await interaction.response.defer()

        # 1. Resgatar Log
        async with self.bot.db.execute("SELECT user_name, content, is_bot FROM session_logs WHERE channel_id = ? ORDER BY id ASC", (interaction.channel_id,)) as cursor:
            logs = await cursor.fetchall()

        if not logs:
            return await interaction.followup.send("📜 A folha está em branco. Nada foi escrito.")

        # 2. Formatar
        texto_bruto = ""
        for nome, conteudo, is_bot in logs:
            prefixo = "[SISTEMA]" if is_bot else f"[{nome}]"
            texto_bruto += f"{prefixo}: {conteudo}\n"

        # 3. Gerar com GPT-4o-Mini (Mais barato e rápido)
        if not client:
            return await interaction.followup.send("❌ API Key da OpenAI não configurada.")

        system_prompt = """
        Você é Dandelion, o bardo poeta de The Witcher.
        Escreva um DIÁRIO NARRATIVO resumindo a sessão de RPG.
        - Ignore comandos técnicos (/rolar, etc).
        - Dramatize os combates e diálogos.
        - Mantenha um tom poético e carismático.
        - Seja conciso.
        """

        # Limite de segurança (aprox 12k tokens input)
        user_message = f"Histórico do chat:\n\n{texto_bruto[-20000:]}"

        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini", # <--- OTIMIZAÇÃO AQUI
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            diario = response.choices[0].message.content

            if len(diario) > 4000: 
                diario = diario[:4000] + "... (continua)"

            embed = discord.Embed(title="📕 As Crônicas da Sessão", description=diario, color=0x7A0000)
            embed.set_footer(text="Escrito por Dandelion (via gpt-4o-mini)")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            log.error(f"Erro no Scribe OpenAI: {e}")
            await interaction.followup.send(f"❌ A pena quebrou (Erro na API): {str(e)}")

    # --- Listener Otimizado ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in self.active_sessions: return
        if message.content.startswith("/"): return

        content = message.content
        is_bot = message.author.bot
        user_name = message.author.display_name

        if is_bot and message.embeds:
            embed = message.embeds[0]
            desc = embed.description if embed.description else ""
            title = embed.title if embed.title else ""
            fields = " | ".join([f"{f.name}: {f.value}" for f in embed.fields])
            content = f"EVENTO: {title} - {desc} {fields}"
        
        if not content: return

        # Dica: Em um bot muito grande, usar um buffer em memória seria melhor
        # mas para campanhas médias, este insert direto é aceitável com aiosqlite.
        try:
            await self.bot.db.execute(
                "INSERT INTO session_logs (channel_id, user_name, content, is_bot) VALUES (?, ?, ?, ?)",
                (message.channel.id, user_name, content, is_bot)
            )
            await self.bot.db.commit()
        except Exception as e:
            log.error(f"Erro ao salvar log: {e}")

async def setup(bot):
    await bot.add_cog(Scribe(bot))