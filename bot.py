import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands

from database import init_db
# Nota: Os imports das Cogs são feitos dinamicamente pelo load_extension, 
# mas mantemos os imports das classes se quisermos add_cog direto (como no original),
# ou usamos load_extension para tudo. Vou manter o original misto para garantir compatibilidade.
from cogs.characters import Characters
from cogs.dice import Dice
from cogs.inventory import Inventory
from cogs.skills import Skills

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Inicializa o DB de forma síncrona antes do bot arrancar
init_db()

class DandelionBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )

    async def setup_hook(self):
        # Cogs carregadas diretamente
        await self.add_cog(Characters(self))
        await self.add_cog(Dice(self))
        await self.add_cog(Inventory(self))
        await self.add_cog(Skills(self))

        # Extensions
        await self.load_extension("cogs.ai_handler")
        await self.load_extension("cogs.bestiary")

        await self.tree.sync()
        print("✅ Bot pronto e comandos sincronizados.")

bot = DandelionBot()

@bot.event
async def on_ready():
    print(f"🚀 Dandelion online como {bot.user}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ Aguarde {error.retry_after:.1f}s.", ephemeral=True
        )
    else:
        # Loga o erro no console para debug
        print(f"Erro no comando: {error}")
        # Tenta avisar o usuário se a interação ainda for válida
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro interno.", ephemeral=True)
        except:
            pass

bot.run(TOKEN)