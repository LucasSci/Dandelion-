import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import json
import base64
from dotenv import load_dotenv
from openai import OpenAI

# ============================
# CARREGA .env
# ============================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ============================
# FUNÇÃO: extrair JSON do modelo
# ============================
def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Nenhum JSON encontrado na resposta do modelo")
    return json.loads(match.group())

# ============================
# COOLDOWN DINÂMICO
# ============================
def cooldown_dinamico(interaction: discord.Interaction):
    texto = interaction.namespace.solicitacao
    size = len(texto)

    if size < 50:
        return app_commands.Cooldown(1, 8)
    elif size < 200:
        return app_commands.Cooldown(1, 20)
    else:
        return app_commands.Cooldown(1, 45)

# ============================
# COG
# ============================
class AIHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não encontrada no .env")

        self.SYSTEM_PROMPT = """
Você é Dandelion, o bardo de Zerrikania no universo The Witcher.

Analise a pergunta do usuário e responda SOMENTE neste JSON:

{
  "needs_image": true ou false,
  "image_prompt": "descrição visual da criatura ou cena, ou null",
  "answer": "resposta ao usuário no estilo do bardo"
}

Regras:
- Se a pergunta for sobre criaturas, lugares, itens, pessoas ou monstros → needs_image = true
- Perguntas conceituais, regras, lore abstrato → needs_image = false
- image_prompt deve ser um prompt detalhado em inglês para geração de imagem
- Nunca escreva nada fora do JSON
- A resposta deve estar em português
"""

    # ============================
    # /dandelion
    # ============================
    @app_commands.command(name="dandelion", description="Fale com Dandelion, o bardo")
    @app_commands.checks.dynamic_cooldown(cooldown_dinamico, key=lambda i: (i.guild_id, i.user.id))
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):

        await interaction.response.defer()

        try:
            # ========================
            # 1️⃣ Pergunta ao GPT
            # ========================
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": solicitacao}
                ],
                temperature=0.7
            )

            raw = response.choices[0].message.content
            data = extract_json(raw)

            needs_image = data.get("needs_image", False)
            answer = data.get("answer", "Erro na resposta.")
            image_prompt = data.get("image_prompt")

            # ========================
            # 2️⃣ Se precisa de imagem
            # ========================
            if needs_image and image_prompt:
                img = client.images.generate(
                    model="gpt-image-1",
                    prompt=image_prompt,
                    size="1024x1024"
                )

                image_base64 = img.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)

                file = discord.File(
                    fp=io.BytesIO(image_bytes),
                    filename="image.png"
                )

                await interaction.followup.send(file=file)

            # ========================
            # 3️⃣ Envia o texto
            # ========================
            embed = discord.Embed(
                title="🪕 Crônicas de Zerrikania",
                description=answer,
                color=0x7A0000
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"❌ O bardo se engasgou nos próprios versos:\n`{str(e)}`",
                ephemeral=True
            )

# ============================
# SETUP
# ============================
async def setup(bot):
    await bot.add_cog(AIHandler(bot))
