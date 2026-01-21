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
