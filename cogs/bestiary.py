import asyncio
import discord
import aiohttp
import os
import base64
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

# --- CONFIGURAÇÕES ---
DB_NAME = 'bestiario.db'
WITCHER_API_URL = "https://witcher.fandom.com/api.php"
WITCHER_THEME_COLOR = 0xC0A080 

# Modelos
OPENAI_TEXT_MODEL = "gpt-4o" 
OPENAI_IMAGE_MODEL = "dall-e-3"

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class Bestiary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- TRADUTOR INTELIGENTE ---
    async def traduzir_nome(self, nome_usuario):
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=OPENAI_TEXT_MODEL,
                messages=[{
                    "role": "system", 
                    "content": "You are a translator. Translate the user input to the OFFICIAL ENGLISH NAME of the monster in The Witcher 3. Return ONLY the name."
                }, {
                    "role": "user", "content": nome_usuario
                }]
            )
            return response.choices[0].message.content.strip()
        except:
            return nome_usuario

    # --- BUSCA NA WIKI ---
    async def buscar_imagem_api(self, termo_busca):
        async with aiohttp.ClientSession() as session:
            try:
                params_busca = {"action": "opensearch", "search": termo_busca, "limit": "1", "format": "json"}
                async with session.get(WITCHER_API_URL, params=params_busca) as resp:
                    if resp.status != 200: return None, None
                    data = await resp.json()
                    if not data[1]: return None, None
                    titulo_oficial = data[1][0]

                params_img = {"action": "query", "titles": titulo_oficial, "prop": "pageimages", "pithumbsize": "1024", "format": "json"}
                async with session.get(WITCHER_API_URL, params=params_img) as resp:
                    if resp.status != 200: return None, None
                    data = await resp.json()
                    pages = data.get("query", {}).get("pages", {})
                    for page_id in pages:
                        if "thumbnail" in pages[page_id]:
                            return pages[page_id]["thumbnail"]["source"], titulo_oficial
                return None, titulo_oficial
            except Exception as e:
                print(f"Erro Wiki: {e}")
                return None, None

    # --- COMANDO PRINCIPAL ---
    @app_commands.command(name="gerar_imagem", description="🎨 Cria arte estilo Witcher 3 Journal")
    @app_commands.describe(nome_monstro="Nome da criatura (Português ou Inglês)")
    async def gerar_imagem(self, interaction: discord.Interaction, nome_monstro: str):
        await interaction.response.defer()

        if not client:
            return await interaction.followup.send("❌ OpenAI API Key não configurada.")

        # 1. TRADUÇÃO
        nome_ingles = await self.traduzir_nome(nome_monstro)
        
        url_referencia = None
        nome_oficial = nome_ingles
        
        # 2. Busca Referência
        async with self.bot.db.execute("SELECT imagem_url, nome FROM criaturas WHERE nome LIKE ?", (f'%{nome_ingles}%',)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                url_referencia = row[0]
                nome_oficial = row[1]

        if not url_referencia:
            url_api, titulo_api = await self.buscar_imagem_api(nome_ingles)
            if url_api:
                url_referencia = url_api
                nome_oficial = titulo_api
            else:
                return await interaction.followup.send(f"❌ Não encontrei referência visual para **{nome_ingles}**.")

        # 3. GPT-4o: CRIAÇÃO DO PROMPT "ESTILO WITCHER"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url_referencia) as resp:
                    image_data = await resp.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')

            # --- AQUI ESTÁ A MÁGICA DO ESTILO ---
            prompt_instruction = f"""
            You are the artist illustrating Dandelion's Bestiary Journal in The Witcher 3.
            Analyze this creature ('{nome_oficial}') and write a prompt for DALL-E 3.
            
            ART STYLE REQUIREMENTS (Strictly follow this):
            1. MEDIUM: Rough ink sketch with watercolor wash.
            2. TEXTURE: Dirty, aged parchment paper background (sepia tones).
            3. LINEWORK: Expressive, messy, thick ink contours, heavy cross-hatching shadows.
            4. VIBE: Grimdark fantasy, eerie, sketchy, not clean. Looks like a field journal drawing.
            5. COLOR: Mostly monochromatic sepia/black with muted, desaturated colors.
            
            SAFETY:
            - Keep the monster scary but avoid excessive gore to pass safety filters.
            - Pose should be dynamic or menacing.
            
            Output ONLY the visual description prompt.
            """
            
            response_gpt = await asyncio.to_thread(
                client.chat.completions.create,
                model=OPENAI_TEXT_MODEL,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt_instruction},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=250
            )
            final_prompt = response_gpt.choices[0].message.content
            
            # 4. DALL-E 3: GERAÇÃO
            await interaction.followup.send(f"🎨 Desenhando **{nome_oficial}** no estilo do jogo... (Aguarde)")
            
            # Reforço de estilo hardcode no prompt final
            dalle_prompt_final = f"Artstyle of The Witcher 3 Bestiary Journal UI. Rough ink sketch on dirty old parchment paper. Heavy cross-hatching shading. Sepia tones. Grimdark fantasy concept art. {final_prompt}"
            
            response_dalle = await asyncio.to_thread(
                client.images.generate,
                model=OPENAI_IMAGE_MODEL,
                prompt=dalle_prompt_final,
                size="1024x1024",
                quality="standard",
                n=1
            )

            image_url = response_dalle.data[0].url
            
            embed = discord.Embed(
                title=f"📜 Bestiário: {nome_oficial}", 
                description=f"*Ilustração encontrada nas anotações de Dandelion.*",
                color=WITCHER_THEME_COLOR
            )
            embed.set_image(url=image_url)
            embed.set_thumbnail(url=url_referencia) # Mostra a original pequena para comparar
            embed.set_footer(text="Geração DALL-E 3 - Estilo Witcher Journal")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            error_msg = str(e)
            if "content_policy" in error_msg:
                await interaction.followup.send("⚠️ **Censura:** O DALL-E achou o monstro violento demais. Tente de novo, às vezes é aleatório.")
            else:
                await interaction.followup.send(f"❌ Erro: {error_msg}")

    # --- COMANDO VER ---
    @app_commands.command(name="ver", description="Consulta ficha do monstro")
    async def ver(self, interaction: discord.Interaction, nome: str):
        # Lógica de consulta ao banco (mantida igual)
        async with self.bot.db.execute("SELECT * FROM criaturas WHERE nome LIKE ?", (f'%{nome}%',)) as cursor:
            data = await cursor.fetchone()
        
        if not data: return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)

        try:
            id_c, nome_real, desc, fraquezas, img_url, hp, ini, dano = data[:8]
        except:
             nome_real = data[1]
             img_url = data[4] if len(data) > 4 else None
             desc, fraquezas, hp, ini, dano = "Sem dados", "Nenhuma", 50, 10, "1d6"

        embed = discord.Embed(title=f"📜 {nome_real.upper()}", description=f"_{desc}_", color=WITCHER_THEME_COLOR)
        embed.add_field(name="⚔️ Status", value=f"HP: {hp} | Ini: {ini} | Dano: {dano}", inline=False)
        if img_url: embed.set_image(url=img_url)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Bestiary(bot))