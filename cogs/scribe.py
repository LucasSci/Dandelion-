import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializa cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
DB_NAME = "bestiario.db"

class Scribe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = set() # IDs dos canais que estão sendo gravados

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
            
            diario = response.choices[0].message.content

            # Cortar se for muito longo para o Discord (limite de 4096 caracteres na descrição do Embed)
            if len(diario) > 4000: 
                diario = diario[:4000] + "... (continua no próximo bardo)"

            embed = discord.Embed(title="📕 As Crônicas da Sessão", description=diario, color=0x7A0000)
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
            await self.bot.db.execute(
                "INSERT INTO session_logs (channel_id, user_name, content, is_bot) VALUES (?, ?, ?, ?)",
                (message.channel.id, user_name, content, is_bot)
            )
            await self.bot.db.commit()
        except Exception as e:
            print(f"Erro ao salvar log: {e}")

async def setup(bot):
    await bot.add_cog(Scribe(bot))