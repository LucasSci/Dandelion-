import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import json
import asyncio
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def extract_json_safe(text):
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE)
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        try:
            return json.loads(text)
        except:
            return {"damage": 0, "status": [], "narration": text}
    return json.loads(match.group(1))

class AIHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SYSTEM_PROMPT = """
        Você é o Mestre do Jogo de um RPG Dark Fantasy (The Witcher).
        Responda SOMENTE neste formato JSON (sem markdown em volta):
        { "damage": int, "status": ["list"], "narration": "string" }
        Se for apenas narração sem dano, coloque damage: 0.
        Seja criativo, descreva o impacto, o sangue e a atmosfera.
        """
    
    async def acoes_autocomplete(self, interaction: discord.Interaction, current: str):
        sugestoes = [
            "Atacar com a espada de prata",
            "Lançar sinal Igni",
            "Investigar os rastros",
            "Tentar intimidar",
            "Esquivar para a esquerda"
        ]
        return [
            app_commands.Choice(name=s, value=s)
            for s in sugestoes if current.lower() in s.lower()
        ]

    @app_commands.command(name="dandelion", description="Fale com o Mestre de Jogo (GPT-4o)")
    @app_commands.autocomplete(solicitacao=acoes_autocomplete)
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
        if not client:
             return await interaction.response.send_message("❌ OpenAI API não configurada.", ephemeral=True)
             
        await interaction.response.defer()

        try:
            # Pega o contexto do combate atual
            combat_cog = self.bot.get_cog("Combat")
            contexto = ""
            if combat_cog:
                try:
                    contexto = combat_cog.obter_resumo_combate(interaction.channel_id)
                except AttributeError:
                    contexto = "Sem combate ativo."
            
            user_prompt = f"Contexto do Combate: {contexto}\nAção do Jogador: {solicitacao}"
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )

            content = response.choices[0].message.content
            data = extract_json_safe(content)
            
            embed = discord.Embed(
                title="🪕 Crônicas de Zerrikania", 
                description=data.get("narration", "..."), 
                color=0x7A0000
            )
            
            dano = data.get("damage", 0)
            if dano > 0:
                embed.add_field(name="💥 Dano Causado", value=f"**{dano}**", inline=True)
            
            status = data.get("status", [])
            if status:
                embed.add_field(name="💀 Status", value=", ".join(status), inline=True)
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro GPT: `{str(e)}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AIHandler(bot))