import os
import discord
import aiosqlite
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands

from database import init_db, DB_NAME
from cogs.characters import Characters
from cogs.dice import Dice
from cogs.inventory import Inventory
from cogs.skills import Skills

# ======================
# CARREGA O .env
# ======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

init_db()

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

    async def setup_hook(self):
        # Conexão persistente com banco de dados (Performance)
        self.db = await aiosqlite.connect(DB_NAME)
        self.db = await aiosqlite.connect(DB_NAME)
        await self.db.execute("PRAGMA foreign_keys = ON")

        # Cogs carregadas diretamente (Classes importadas)
        await self.add_cog(Characters(self))
        await self.add_cog(Dice(self))
        await self.add_cog(Inventory(self))
        #await self.add_cog(Skills(self))

        # Cogs carregadas como extensões (Arquivos na pasta cogs)
        await self.load_extension("cogs.ai_handler")
        await self.load_extension("cogs.bestiary")
        
        # --- AQUI ESTAVA FALTANDO O COMBATE ---
        try:
            await self.load_extension("cogs.combat")
            print("⚔️ Sistema de Combate carregado.")
        except Exception as e:
            print(f"❌ Erro ao carregar combate: {e}")
        # --------------------------------------

        # Sincroniza os slash commands
        await self.tree.sync()
        print("✅ Bot pronto e comandos sincronizados.")

    async def close(self):
        if hasattr(self, 'db') and self.db:
            if self.db:
                await self.db.close()
            await super().close()

bot = DandelionBot()

# ======================
# EVENTO DE CONEXÃO
# ======================
@bot.event
async def on_ready():
    print(f"🚀 Dandelion online como {bot.user}")

# ======================
# TRATAMENTO GLOBAL DE ERROS
# ======================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ **Aguarde {error.retry_after:.1f}s antes de chamar o bardo novamente.**",
            ephemeral=True
        )
    else:
        # Se for erro de comando não encontrado ou check failure, avisa
        print(f"Erro no comando: {error}")

# ======================
# INICIA O BOT
# ======================
bot.run(TOKEN)