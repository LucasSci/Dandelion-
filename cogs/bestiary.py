import asyncio
import discord
import re
import aiosqlite
import aiohttp
from discord import app_commands
from discord.ext import commands
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- CONFIGURAÇÕES ---
DB_NAME = 'bestiario.db'
WITCHER_WIKI_URL = "https://witcher.fandom.com"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0'}

class Bestiary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = GoogleTranslator(source='en', target='pt')

    # --- UTILITÁRIOS ---
    def _sanitizar_texto(self, texto):
        if not texto: return ""
        texto = re.sub(r'\[\d+\]', '', texto)
        texto = re.sub(r'\n\s*\n', '\n', texto)
        texto = texto.replace('Editar', '').replace('\u200b', '')
        return texto.strip()

    def _processar_dados_tecnicos(self, texto_bruto):
        curtos, longos = [], {}
        chave_atual = None
        listas_detectadas = ["Saque", "Loot", "Suscetibilidade", "Susceptibility", "Variações"]

        if not texto_bruto: return curtos, longos

        for linha in texto_bruto.split('\n'):
            linha = self._sanitizar_texto(linha)
            if not linha: continue

            if ":" in linha:
                label, valor = linha.split(":", 1)
                label, valor = label.strip(), valor.strip()
                if any(c in label for c in listas_detectadas):
                    chave_atual = label
                    longos[chave_atual] = [valor] if valor else []
                else:
                    chave_atual = None
                    if valor and "Desconhecido" not in valor:
                        curtos.append((label, valor))
            elif chave_atual:
                longos[chave_atual].append(linha)
        return curtos, longos

    def _gerar_embed_grimorio(self, nome, desc, fraquezas, img_url):
        embed = discord.Embed(title=f"› {nome.upper()} ‹", color=0x1a1a1a)
        if img_url: 
            embed.set_thumbnail(url=img_url)

        lore = self._sanitizar_texto(desc)
        embed.add_field(name="📘 Entrada do Bestiário", value=f"{lore[:1200]}", inline=False)

        curtos, longos = self._processar_dados_tecnicos(fraquezas)
        
        if curtos:
            embed.add_field(name="⠀", value="**▬▬ ɪɴғᴏʀᴍᴀçõᴇs ▬▬**", inline=False)
            for l, v in curtos[:6]:
                embed.add_field(name=f"◈ {l}", value=f"`{v}`", inline=True)

        for l, itens in longos.items():
            lista = "\n".join([f"• {i}" for i in itens if i])
            if lista:
                embed.add_field(name=f"🔸 {l}", value=f"```Is\n{lista[:500]}```", inline=False)

        embed.set_footer(text="Registro Oficial • Zerrikania RPG")
        return embed

    # --- COMANDOS ---

    async def criatura_autocomplete(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('SELECT nome FROM criaturas WHERE nome LIKE ? LIMIT 10', (f'%{current}%',)) as cursor:
                rows = await cursor.fetchall()
                return [app_commands.Choice(name=n[0], value=n[0]) for n in rows]

    @app_commands.command(name="ver", description="Consulta rápida de uma criatura")
    @app_commands.autocomplete(nome=criatura_autocomplete)
    async def ver(self, interaction: discord.Interaction, nome: str):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute('SELECT nome, descricao, fraquezas, imagem_url FROM criaturas WHERE nome = ?', (nome,)) as cursor:
                res = await cursor.fetchone()
        
        if res:
            await interaction.response.send_message(embed=self._gerar_embed_grimorio(*res))
        else:
            await interaction.response.send_message("🔍 Criatura não encontrada.", ephemeral=True)

    @app_commands.command(name="alimentar_bestiario", description="⚙️ Importação em massa da Wiki")
    async def alimentar_bestiario(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔍 Iniciando rastreamento...")
        cat_url = f"{WITCHER_WIKI_URL}/wiki/Category:The_Witcher_3_bestiary"

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(cat_url) as resp:
                if resp.status != 200: 
                    return await interaction.edit_original_response(content="❌ Falha na Wiki.")
                
                html = await resp.text()
                # Processa HTML em thread separada
                soup = await asyncio.to_thread(BeautifulSoup, html, 'html.parser')
                links = [(a.text.strip(), WITCHER_WIKI_URL + a.get('href')) 
                         for a in soup.select('.category-page__member-link')]

                for i, (nome, url) in enumerate(links, 1):
                    await self._extrair_e_salvar(session, nome, url)
                    if i % 5 == 0: # Atualiza a cada 5 para não floodar
                        await interaction.edit_original_response(content=f"🔄 Progresso: {i}/{len(links)} (Último: {nome})")
                    await asyncio.sleep(1)

        await interaction.edit_original_response(content="✅ Bestiário alimentado e traduzido!")

    @app_commands.command(name="monstro_editar", description="Define atributos de combate de uma criatura")
    async def monstro_editar(self, interaction: discord.Interaction, nome: str, hp: int, iniciativa: int):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
                UPDATE criaturas SET hp_max = ?, iniciativa = ?
                WHERE nome = ?
            """, (hp, iniciativa, nome))
            await db.commit()
            
            if cursor.rowcount > 0:
                await interaction.response.send_message(f"✅ **{nome}** atualizado: HP Máximo {hp} | Iniciativa {iniciativa}")
            else:
                await interaction.response.send_message(f"❌ O monstro **{nome}** não existe no bestiário! Use `/alimentar_bestiario` primeiro.", ephemeral=True)

    # --- LÓGICA INTERNA DE EXTRAÇÃO ---
    async def _extrair_e_salvar(self, session, nome, url):
        async with session.get(url) as resp:
            if resp.status != 200: return False
            
            html = await resp.text()
            soup = await asyncio.to_thread(BeautifulSoup, html, 'html.parser')
            
            content = soup.find('div', {'class': 'mw-parser-output'})
            if not content: return False

            lore_raw = ""
            for el in content.find_all(['h2', 'p'], recursive=False)[:8]:
                if len(el.text.strip()) > 30: lore_raw += el.text.strip() + "\n\n"

            detalhes_raw = []
            img_url = None
            infobox = soup.find('aside', {'class': 'portable-infobox'})
            if infobox:
                img_tag = infobox.find('img', {'class': 'pi-image-thumbnail'})
                if img_tag: img_url = img_tag.get('src')
                for item in infobox.find_all('div', {'class': 'pi-item pi-data'}):
                    h3 = item.find('h3')
                    val = item.find('div', {'class': 'pi-data-value'})
                    if h3 and val:
                        detalhes_raw.append(f"{h3.text.strip()}: {val.text.strip()}")

            # Tradução (Executa em thread para não bloquear)
            lore_pt = await asyncio.to_thread(self.translator.translate, lore_raw[:1200])
            detalhes_texto = "\n".join(detalhes_raw)
            if detalhes_texto:
                detalhes_pt = await asyncio.to_thread(self.translator.translate, detalhes_texto)
            else:
                detalhes_pt = ""

            lore_pt = self._sanitizar_texto(lore_pt)
            detalhes_pt = self._sanitizar_texto(detalhes_pt)

            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO criaturas (nome, descricao, fraquezas, imagem_url) 
                    VALUES (?, ?, ?, ?)
                ''', (nome, lore_pt, detalhes_pt, img_url))
                await db.commit()
            return True

async def setup(bot):
    await bot.add_cog(Bestiary(bot))