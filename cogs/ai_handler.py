import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import json
import io
import time
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================
# ENV
# ============================

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY não encontrado")
if not DEEPAI_API_KEY:
    raise ValueError("❌ DEEPAI_API_KEY não encontrado")

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
Você é Dandelion, o bardo do universo The Witcher narrando Zerrikania.

Analise a pergunta e responda SOMENTE neste JSON:

{
  "needs_image": true ou false,
  "image_prompt": "descrição detalhada da criatura, objeto ou cena",
  "answer": "resposta narrativa ao usuário"
}

Regras:
- needs_image deve ser true se a pergunta mencionar criatura, monstro, item, pessoa, local, cena ou algo visual.
- image_prompt deve ser extremamente detalhado se needs_image = true.
- Estilo visual: The Witcher 3, dark fantasy, realista, iluminação cinematográfica, alta definição.
- Nunca escreva nada fora do JSON.
- Português brasileiro.
"""

    @app_commands.command(name="dandelion", description="Fale com Dandelion, o bardo de Zerrikania")
    @app_commands.checks.dynamic_cooldown(cooldown_dinamico, key=lambda i: (i.guild_id, i.user.id))
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
        await interaction.response.defer()

        try:
            # =========================
            # 1️⃣ Gemini interpreta
            # =========================
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=solicitacao,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=0.7
                )
            )

            data = extract_json(response.text)

            needs_image = data.get("needs_image", False)
            image_prompt = data.get("image_prompt")
            answer = data.get("answer", "O bardo perdeu o fio da canção.")

            file = None

            # =========================
            # 2️⃣ Se precisar imagem → DeepAI
            # =========================
            if needs_image and image_prompt:
                final_prompt = f"""
{image_prompt}
Style: The Witcher 3, dark fantasy, ultra realistic, cinematic lighting,
gritty medieval fantasy, detailed textures, epic atmosphere
"""

                headers = {
                    "api-key": DEEPAI_API_KEY
                }

                payload = {
                    "text": final_prompt
                }

                r = requests.post(
                    "https://api.deepai.org/api/text2img",
                    headers=headers,
                    data=payload,
                    timeout=90
                )

                if r.status_code != 200:
                    raise Exception(f"DeepAI erro {r.status_code}: {r.text}")

                img_url = r.json()["output_url"]
                img_bytes = requests.get(img_url).content

                file = discord.File(
                    fp=io.BytesIO(img_bytes),
                    filename="zerrikania.png"
                )

            # =========================
            # 3️⃣ Embed
            # =========================
            embed = discord.Embed(
                title="🪕 Crônicas de Zerrikania",
                description=answer,
                color=0x7A0000
            )

            if file:
                embed.set_image(url="attachment://zerrikania.png")

            embed.set_footer(
                text="Gemini 2.5 + DeepAI",
                icon_url=self.bot.user.display_avatar.url
            )

            if file:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"❌ O bardo tropeçou nos próprios versos:\n`{str(e)}`",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AIHandler(bot))
