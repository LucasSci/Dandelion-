import asyncio
from http import client
import logging
from contextlib import suppress

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from database import DB_NAME, init_db
from cogs.characters import Characters
from cogs.dice import Dice
from cogs.inventory import Inventory
from cogs.skills import Skills
import types

init_db()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("dandelion.bot")

# ======================
# CLASSE DO BOT
# ======================
class DandelionBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
        self.db = None
        self.http_session = None

    async def setup_hook(self):
        timeout = aiohttp.ClientTimeout(total=settings.http_timeout_seconds)
        self.http_session = aiohttp.ClientSession(timeout=timeout)

        # Conexão persistente com banco de dados
        self.db = await aiosqlite.connect(DB_NAME)
        await self.db.execute("PRAGMA foreign_keys = ON")

        # Cogs carregadas diretamente
        await self.add_cog(Characters(self))
        await self.add_cog(Dice(self))
        await self.add_cog(Inventory(self))
        await self.add_cog(Skills(self))
        for ext in settings.optional_extensions:
            try:
                await self.load_extension(ext)
                logger.info("Extensão opcional carregada: %s", ext)
            except Exception as e:
                logger.warning("Falha ao carregar extensão opcional %s: %s", ext, e)

        # Carregamento seguro de extensões
        for ext in settings.extensions:
            try:
                await self.load_extension(ext)
                logger.info("Extensão carregada: %s", ext)
            except Exception as e:
                logger.exception("Falha ao carregar extensão %s", ext)

        # Sincroniza os slash commands
        if settings.sync_commands:
            await self.tree.sync()
            logger.info("Bot pronto e comandos sincronizados.")
        else:
            logger.info("Bot pronto. Sincronização de comandos desativada.")

    async def close(self):
        if hasattr(self, 'db') and self.db:
            await self.db.close()
        if self.http_session:
            await self.http_session.close()
        await super().close()

bot = DandelionBot()

# ======================
# COMANDO DE TESTE: GERAÇÃO DE PROMPT (IA)
# ======================
@bot.tree.command(name="teste_gerar_prompt", description="[DEV] Gera um prompt de imagem baseado em uma URL")
@app_commands.describe(url_imagem="A URL da imagem de referência da Fandom")
async def teste_gerar_prompt(interaction: discord.Interaction, url_imagem: str):
    await interaction.response.defer()

    if not client:
        return await interaction.followup.send("❌ Gemini API não configurada.")
    if not bot.http_session:
        return await interaction.followup.send("❌ Sessão HTTP indisponível.")
    max_image_bytes = 5 *1024 * 1024

    try:
        # 1. Baixar a imagem da URL para a memória
        async with bot.http_session.get(url_imagem) as resp:
            if resp.status != 200:
                return await interaction.followup.send("❌ Não consegui acessar a imagem na URL fornecida.")
            content_length = resp.content_length
            if content_length is not None and content_length > max_image_bytes:
                return await interaction.followup.send("❌ A imagem excede 5MB. Use uma imagem menor.")
            image_data = await resp.content.read(max_image_bytes + 1)
            if len(image_data) > max_image_bytes:
                return await interaction.followup.send("❌ A imagem excede 5MB. Use uma imagem menor.")
            image_data = await resp.read()

        # 2. Enviar para o Gemini Vision
        prompt_text = """
        Analise esta imagem de uma criatura.
        Crie um prompt de geração de imagem (text-to-image) altamente detalhado para recriar esta criatura.
        O estilo deve ser: "Dark fantasy RPG concept art, estilo The Witcher 3, alta resolução, 8k, texturas realistas, iluminação dramática".
        Descreva a anatomia, a pose, as texturas da pele/pelo e o ambiente com base na imagem de referência.
        Retorne APENAS o prompt em inglês.
        """
        
        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(text=prompt_text),
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
                ]
            )
        ]

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=contents
        )

        prompt_gerado = response.text

        embed = discord.Embed(title="🎨 Prompt Gerado pelo Gemini", description=prompt_gerado[:4000], color=0x00FF00)
        embed.set_thumbnail(url=url_imagem)
        embed.set_footer(text="Copie este prompt e use no Midjourney/Leonardo.ai")
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.exception("Falha no comando teste_gerar_prompt")
        await interaction.followup.send("❌ Erro na análise da IA. Consulte os logs.")

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    logger.info("Dandelion online como %s", bot.user)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ **Aguarde {error.retry_after:.1f}s.**", ephemeral=True
        )
    else:
        logger.exception("Erro no comando", exc_info=error)
        with suppress(discord.InteractionResponded):
            await interaction.response.send_message("❌ Ocorreu um erro inesperado.", ephemeral=True)

if __name__ == "__main__":
    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN não configurado no arquivo .env.")
    bot.run(settings.discord_token)
