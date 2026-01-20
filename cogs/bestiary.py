import asyncio
import base64
import os
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

from database import (
    SEED_LOCATIONS_SQL,
    SEED_LOOKUPS_SQL,
    SEED_MONSTERS_SQL,
    SEED_RELATIONS_SQL,
    SEEDS_DIR,
)
from utils import rolar_pericia_explosiva
from witcher_rules import rolar_pericia

# --- CONFIGURAÇÕES ---
DB_NAME = 'bestiario.db'
WITCHER_API_URL = "https://witcher.fandom.com/api.php"
WITCHER_THEME_COLOR = 0xC0A080 
DEFAULT_MONSTER_LORE_CD = 14
MONSTER_LORE_STAT_KEYS = ("int", "inteligencia", "inteligência", "intelligence")
MONSTER_LORE_SKILL_KEYS = (
    "monster lore",
    "lore de monstros",
    "conhecimento de monstros",
    "conhecimento de monstro",
    "lore de monstro",
)

# Modelos
OPENAI_TEXT_MODEL = "gpt-4o" 
OPENAI_IMAGE_MODEL = "dall-e-3"

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


class Bestiary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.seed_files = [
            "seed_bestiary_ecosystem.sql",
            "seed_tw3_full_by_category.sql",
            "seed_books_core.sql",
            "seed_books_core_lote2.sql",
            "seed_tw2_full.sql",
            "seed_dlcs_hos_baw.sql",
            "seed_named_monsters_core.sql",
        ]

    async def _aplicar_seeds(self) -> list[str]:
        aplicados = []
        for filename in self.seed_files:
            seed_path = SEEDS_DIR / filename
            if not seed_path.exists():
                continue
            script = seed_path.read_text(encoding="utf-8")
            await self.bot.db.executescript(script)
            try:
                display_path = seed_path.relative_to(Path.cwd())
            except ValueError:
                display_path = seed_path
            aplicados.append(str(display_path))

        await self.bot.db.executescript(SEED_LOOKUPS_SQL)
        await self.bot.db.executescript(SEED_LOCATIONS_SQL)
        await self.bot.db.executescript(SEED_MONSTERS_SQL)
        await self.bot.db.executescript(SEED_RELATIONS_SQL)
        await self.bot.db.commit()
        return aplicados

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

    async def _buscar_personagem(self, user_id: int):
        async with self.bot.db.execute(
            "SELECT id, nome FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def _buscar_atributos(self, personagem_id: int) -> dict[str, int]:
        async with self.bot.db.execute(
            "SELECT nome, valor FROM atributos_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return {nome.strip().lower(): valor for nome, valor in rows}

    def _obter_valor_atributo(self, atributos: dict[str, int], chaves: tuple[str, ...]) -> int | None:
        for chave in chaves:
            valor = atributos.get(chave)
            if valor is not None:
                return valor
        return None

    def _formatar_rolagens(self, rolagens: list[int], direcao: int) -> str:
        texto = ", ".join(str(r) for r in rolagens)
        if direcao == 1:
            return f"{texto} (explosão ↑)"
        if direcao == -1:
            return f"{texto} (explosão ↓)"
        return texto

    async def _rolar_monster_lore(self, user_id: int, cd: int) -> dict[str, str | bool]:
        personagem = await self._buscar_personagem(user_id)
        if not personagem:
            return {
                "sucesso": False,
                "mensagem": "❌ Você precisa de uma ficha para testar Monster Lore.",
            }

        personagem_id, personagem_nome = personagem
        atributos = await self._buscar_atributos(personagem_id)
        stat = self._obter_valor_atributo(atributos, MONSTER_LORE_STAT_KEYS)
        skill = self._obter_valor_atributo(atributos, MONSTER_LORE_SKILL_KEYS)

        faltando = []
        if stat is None:
            faltando.append("stat INT")
        if skill is None:
            faltando.append("perícia Monster Lore")
        if faltando:
            return {
                "sucesso": False,
                "mensagem": (
                    "⚠️ Falta configurar "
                    + " e ".join(faltando)
                    + f" na ficha de **{personagem_nome}**."
                ),
            }

        rolagens, total, direcao = rolar_pericia_explosiva(stat, skill)
        rolagens_txt = self._formatar_rolagens(rolagens, direcao)
        sucesso = total >= cd
        mensagem = (
            f"🎲 Rolagens: {rolagens_txt}\n"
            f"📌 INT {stat} + Monster Lore {skill} = **{total}** vs CD **{cd}**\n"
            f"{'✅ Sucesso!' if sucesso else '❌ Falhou.'}"
        )
        return {"sucesso": sucesso, "mensagem": mensagem}

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
    @app_commands.describe(
        nome="Nome (ou parte) da criatura",
        cd="CD opcional para Monster Lore (sobrescreve o valor do monstro)",
    )
    async def ver(self, interaction: discord.Interaction, nome: str, cd: int | None = None):
        # Lógica de consulta ao banco (mantida igual)
        async with self.bot.db.execute("SELECT * FROM criaturas WHERE nome LIKE ?", (f'%{nome}%',)) as cursor:
            data = await cursor.fetchone()
        
        if not data: return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)

        dados = list(data) + [None] * (9 - len(data))
        id_c, nome_real, desc, fraquezas, img_url, hp, ini, dano, lore_cd = dados[:9]
        desc = desc or "Sem dados"
        fraquezas = fraquezas or "Nenhuma"
        hp = hp or 50
        ini = ini or 10
        dano = dano or "1d6"
        cd_final = cd if cd is not None else (lore_cd if lore_cd is not None else DEFAULT_MONSTER_LORE_CD)

        show_weaknesses = is_mestre(interaction) or cd <= 0
        roll_detail = None
        if not show_weaknesses:
            async with self.bot.db.execute(
                "SELECT id FROM personagens WHERE user_id = ?",
                (interaction.user.id,),
            ) as cursor:
                personagem = await cursor.fetchone()

            stat_int = 1
            skill_lore = 0
            if personagem:
                personagem_id = personagem[0]
                async with self.bot.db.execute(
                    "SELECT valor FROM atributos_personagem WHERE personagem_id = ? AND nome = 'INT'",
                    (personagem_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                if row:
                    stat_int = max(1, row[0])

                async with self.bot.db.execute(
                    """
                    SELECT valor FROM atributos_personagem
                    WHERE personagem_id = ? AND nome IN ('Monster Lore', 'Conhecimento de Monstros')
                    ORDER BY valor DESC
                    LIMIT 1
                    """,
                    (personagem_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                if row:
                    skill_lore = max(0, row[0])

            roll_result = rolar_pericia(stat_int, skill_lore)
            roll_detail = (
                f"🎲 {roll_result.rolls} + INT({stat_int}) + Skill({skill_lore}) = {roll_result.total}"
            )
            show_weaknesses = roll_result.total >= cd

        embed = discord.Embed(title=f"📜 {nome_real.upper()}", description=f"_{desc}_", color=WITCHER_THEME_COLOR)
        embed.add_field(name="⚔️ Status", value=f"HP: {hp} | Ini: {ini} | Dano: {dano}", inline=False)
        resultado_lore = await self._rolar_monster_lore(interaction.user.id, cd_final)
        if resultado_lore["sucesso"]:
            fraquezas_visiveis = fraquezas
        else:
            fraquezas_visiveis = "🔒 Fraquezas ocultas. Passe no teste de Monster Lore."

        embed.add_field(name="🧠 Monster Lore", value=resultado_lore["mensagem"], inline=False)
        embed.add_field(name="☠️ Fraquezas", value=fraquezas_visiveis, inline=False)
        if img_url:
            embed.set_image(url=img_url)
        if show_weaknesses:
            embed.add_field(name="🧪 Fraquezas", value=fraquezas or "Nenhuma", inline=False)
        else:
            embed.add_field(
                name="🧪 Fraquezas",
                value=f"Ocultas. Teste Monster Lore (CD {cd}) falhou.",
                inline=False,
            )
        if roll_detail and not is_mestre(interaction):
            embed.add_field(name="📚 Witcher Knowledge", value=roll_detail, inline=False)
        if img_url: embed.set_image(url=img_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="alimentar_bestiario",
        description="🔒 Importa seeds do bestiário e atualiza tabelas base.",
    )
    @app_commands.check(is_mestre)
    async def alimentar_bestiario(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        aplicados = await self._aplicar_seeds()
        if not aplicados:
            return await interaction.followup.send(
                "⚠️ Nenhum arquivo de seed encontrado. Mantive apenas os seeds internos.",
                ephemeral=True,
            )
        detalhes = "\n".join(f"• {path}" for path in aplicados)
        await interaction.followup.send(
            f"✅ Seeds aplicados com sucesso:\n{detalhes}",
            ephemeral=True,
        )

    @app_commands.command(
        name="monstro_editar",
        description="🔒 Ajusta HP, iniciativa e dano de um monstro do bestiário.",
    )
    @app_commands.describe(
        nome="Nome (ou parte) da criatura",
        hp_max="Novo HP máximo",
        iniciativa="Nova iniciativa",
        dano_base="Nova fórmula de dano (ex: 2d6+3)",
        lore_cd="CD de Monster Lore (deixe vazio para padrão)",
    )
    @app_commands.check(is_mestre)
    async def monstro_editar(
        self,
        interaction: discord.Interaction,
        nome: str,
        hp_max: int | None = None,
        iniciativa: int | None = None,
        dano_base: str | None = None,
        lore_cd: int | None = None,
    ):
        if hp_max is None and iniciativa is None and dano_base is None and lore_cd is None:
            return await interaction.response.send_message(
                "⚠️ Informe ao menos um campo para atualizar.", ephemeral=True
            )

        async with self.bot.db.execute(
            "SELECT id, nome, hp_max, iniciativa, dano_base, lore_cd FROM criaturas WHERE nome LIKE ? ORDER BY nome LIMIT 1",
            (f"%{nome}%",),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ Monstro não encontrado no bestiário.", ephemeral=True
            )

        criatura_id, nome_real, hp_atual, ini_atual, dano_atual, lore_cd_atual = row
        novos_valores = {
            "hp_max": hp_atual if hp_max is None else hp_max,
            "iniciativa": ini_atual if iniciativa is None else iniciativa,
            "dano_base": dano_atual if dano_base is None else dano_base,
            "lore_cd": lore_cd_atual if lore_cd is None else lore_cd,
        }

        await self.bot.db.execute(
            "UPDATE criaturas SET hp_max = ?, iniciativa = ?, dano_base = ?, lore_cd = ? WHERE id = ?",
            (
                novos_valores["hp_max"],
                novos_valores["iniciativa"],
                novos_valores["dano_base"],
                novos_valores["lore_cd"],
                criatura_id,
            ),
        )
        await self.bot.db.commit()

        detalhes = [
            f"• HP: {hp_atual} → {novos_valores['hp_max']}",
            f"• Iniciativa: {ini_atual} → {novos_valores['iniciativa']}",
            f"• Dano: {dano_atual} → {novos_valores['dano_base']}",
        ]
        if lore_cd is not None:
            cd_atual_txt = lore_cd_atual if lore_cd_atual is not None else f"Padrão ({DEFAULT_MONSTER_LORE_CD})"
            cd_novo_txt = novos_valores["lore_cd"] if novos_valores["lore_cd"] is not None else f"Padrão ({DEFAULT_MONSTER_LORE_CD})"
            detalhes.append(f"• CD Lore: {cd_atual_txt} → {cd_novo_txt}")

        await interaction.response.send_message(
            f"✅ **{nome_real}** atualizado.\n" + "\n".join(detalhes),
            ephemeral=True,
        )

async def setup(bot):
    await bot.add_cog(Bestiary(bot))
