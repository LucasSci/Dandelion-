import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================
# ENV
# ============================

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY não encontrado")

client = genai.Client(api_key=GEMINI_API_KEY)

# ============================
# JSON extractor
# ============================

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("JSON não encontrado")
    return json.loads(match.group())

# ============================
# Cooldown dinâmico
# ============================

def cooldown_dinamico(interaction: discord.Interaction):
    texto = interaction.namespace.solicitacao
    size = len(texto)

    if size < 50:
        return app_commands.Cooldown(1, 10)
    elif size < 200:
        return app_commands.Cooldown(1, 25)
    else:
        return app_commands.Cooldown(1, 60)

# ============================
# COG
# ============================

class AIHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.SYSTEM_PROMPT = """
Você é o Mestre do Jogo de Zerrikania (dark fantasy estilo The Witcher).

Estado atual:
Jogador: {HP, mana}
Inimigo: {nome, hp, status}

O jogador disse: {mensagem}

Responda SOMENTE neste JSON:

{
  "damage": numero,
  "status": ["burn", "stun"],
  "narration": "texto"
}

Regras:
- damage deve ser um inteiro >= 0
- status pode ser lista vazia
- Nunca escreva nada fora do JSON
- Português brasileiro
"""

    @app_commands.command(
        name="dandelion",
        description="Fale com Dandelion, o Mestre de Jogo de Zerrikania"
    )
    @app_commands.checks.dynamic_cooldown(
        cooldown_dinamico,
        key=lambda i: (i.guild_id, i.user.id)
    )
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
        await interaction.response.defer()

        try:
            # ⚙️ Aqui depois você vai injetar o estado real do banco
            estado = """
Jogador: HP 30, Mana 20
Inimigo: Nekker, HP 40, status nenhum
"""

            prompt = self.SYSTEM_PROMPT.replace("{mensagem}", solicitacao)
            prompt = prompt.replace("{HP, mana}", "HP 30, Mana 20")
            prompt = prompt.replace("{nome, hp, status}", "Nekker, HP 40, nenhum")

            # =========================
            # Gemini decide o turno
            # =========================
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )

            data = extract_json(response.text)

            damage = int(data.get("damage", 0))
            status = data.get("status", [])
            narration = data.get("narration", "O destino ficou em silêncio.")

            # ⚔️ Aqui depois você aplica o dano no banco
            # ex: engine.combat.apply_damage(monstro_id, damage, status)

            embed = discord.Embed(
                title="🪕 Crônicas de Zerrikania",
                description=narration,
                color=0x7A0000
            )

            embed.add_field(name="Dano", value=f"**{damage}**", inline=True)
            embed.add_field(name="Status", value=", ".join(status) if status else "Nenhum", inline=True)

            embed.set_footer(
                text="Gemini 2.5 • Mestre do Jogo",
                icon_url=self.bot.user.display_avatar.url
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"❌ O bardo tropeçou nos próprios versos:\n`{str(e)}`",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AIHandler(bot))
