import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # Aviso para não parar o import se faltar a key, mas vai dar erro ao usar
    print("⚠️ GEMINI_API_KEY não encontrado no .env")

# Tenta criar o client apenas se a key existir
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
@app_commands.command(...)
async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
    combat_cog = self.bot.get_cog("Combat")
    contexto = combat_cog.obter_resumo_combate(interaction.channel_id) if combat_cog else ""
    
    prompt = f"{self.SYSTEM_PROMPT}\nContexto: {contexto}\nAção do Jogador: {solicitacao}"
    
def extract_json_safe(text):
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE)
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        try:
            return json.loads(text)
        except:
            return {"damage": 0, "status": [], "narration": text}
    return json.loads(match.group(1))

def cooldown_dinamico(interaction: discord.Interaction):
    texto = interaction.namespace.solicitacao or ""
    size = len(texto)
    if size < 50: return app_commands.Cooldown(1, 10)
    elif size < 200: return app_commands.Cooldown(1, 25)
    else: return app_commands.Cooldown(1, 60)

class AIHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.SYSTEM_PROMPT = """
Você é o Mestre do Jogo de Zerrikania (dark fantasy).
Responda SOMENTE neste JSON:
{ "damage": int, "status": ["list"], "narration": "string" }
"""
    
    async def acoes_autocomplete(self, interaction: discord.Interaction, current: str):
        sugestoes = [
            "Atacar com a espada",
            "Lançar sinal Igni",
            "Procurar pistas com sentidos de bruxo",
            "Tentar intimidar o oponente",
            "Esquivar e contra-atacar"
        ]
        return [
            app_commands.Choice(name=s, value=s)
            for s in sugestoes if current.lower() in s.lower()
        ]

    @app_commands.command(name="dandelion", description="Fale com o Mestre de Jogo")
    @app_commands.autocomplete(solicitacao=acoes_autocomplete) # <--- AQUI
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
        if not client:
             return await interaction.response.send_message("❌ IA não configurada.", ephemeral=True)
             
        await interaction.response.defer()

        try:
            prompt = f"{self.SYSTEM_PROMPT}\nJogador: {solicitacao}"
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )

            data = extract_json_safe(response.text)
            
            embed = discord.Embed(
                title="🪕 Crônicas de Zerrikania", 
                description=data.get("narration", "..."), 
                color=0x7A0000
            )
            embed.add_field(name="Dano", value=str(data.get("damage", 0)), inline=True)
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: `{str(e)}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AIHandler(bot))

