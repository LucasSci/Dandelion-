import os
import discord
import aiosqlite
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands
from google import genai
from google.genai import types
import asyncio
import json
from database import init_db, DB_NAME
from cogs.characters import Characters
from cogs.dice import Dice
from cogs.inventory import Inventory
from cogs.skills import Skills

# ======================
# CARREGA O .env E CONFIGURA IA
# ======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializa o Client do Gemini aqui no bot.py também
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

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
        # Conexão persistente com banco de dados
        self.db = await aiosqlite.connect(DB_NAME)
        await self.db.execute("PRAGMA foreign_keys = ON")

        # Cogs carregadas diretamente
        await self.add_cog(Characters(self))
        await self.add_cog(Dice(self))
        await self.add_cog(Inventory(self))
        await self.add_cog(Skills(self))

        # Carregamento seguro de extensões
        extensoes = ["cogs.ai_handler", "cogs.bestiary", "cogs.combat"]
        for ext in extensoes:
            try:
                await self.load_extension(ext)
                print(f"✅ Extensão carregada: {ext}")
            except Exception as e:
                print(f"❌ Falha ao carregar {ext}: {e}")

        # Sincroniza os slash commands
        await self.tree.sync()
        print("✅ Bot pronto e comandos sincronizados.")

    async def close(self):
        if hasattr(self, 'db') and self.db:
            await self.db.close()
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

    try:
        # 1. Baixar a imagem da URL para a memória
        async with aiohttp.ClientSession() as session:
            async with session.get(url_imagem) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Não consegui acessar a imagem na URL fornecida.")
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
        await interaction.followup.send(f"❌ Erro na análise da IA: {e}")

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🚀 Dandelion online como {bot.user}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ **Aguarde {error.retry_after:.1f}s.**", ephemeral=True
        )
    else:
        print(f"Erro no comando: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)