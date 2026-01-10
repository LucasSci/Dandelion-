import asyncio
import discord
import re
import sqlite3
import aiohttp
from discord import app_commands, ui
from discord.ext import commands
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- CONFIGURAÇÕES ---
DB_PATH = 'bestiario.db'
WITCHER_WIKI_URL = "https://witcher.fandom.com"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0'}

class Bestiary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = GoogleTranslator(source='en', target='pt')

    # --- MÉTODO CENTRAL DE LIMPEZA ---
    def _sanitizar_texto(self, texto):
        """Remove ruídos de HTML, citações da Wiki e excesso de espaços."""
        if not texto: return ""
        texto = re.sub(r'\[\d+\]', '', texto) # Remove [1], [2]
        texto = re.sub(r'\n\s*\n', '\n', texto) # Compacta quebras de linha
        texto = texto.replace('Editar', '').replace('\u200b', '')
        return texto.strip()

    def _processar_dados_tecnicos(self, texto_bruto):
        """Organiza a 'Ficha Técnica' para o layout de colunas."""
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

    # --- CONSTRUTOR DE VISUAL (EMBED) ---
    def _gerar_embed_grimorio(self, nome, desc, fraquezas, img_url):
        """Cria o layout padronizado com imagem no canto (Thumbnail)."""
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

    # --- COMANDOS DE BUSCA E PUBLICAÇÃO ---
    async def criatura_autocomplete(self, interaction: discord.Interaction, current: str):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM criaturas WHERE nome LIKE ? LIMIT 10', (f'%{current}%',))
            return [app_commands.Choice(name=n[0], value=n[0]) for n in cursor.fetchall()]

    @app_commands.command(name="ver", description="Consulta rápida de uma criatura")
    @app_commands.autocomplete(nome=criatura_autocomplete)
    async def ver(self, interaction: discord.Interaction, nome: str):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nome, descricao, fraquezas, imagem_url FROM criaturas WHERE nome = ?', (nome,))
            res = cursor.fetchone()
        
        if res:
            await interaction.response.send_message(embed=self._gerar_embed_grimorio(*res))
        else:
            await interaction.response.send_message("🔍 Criatura não encontrada.", ephemeral=True)

    # --- LÓGICA DO RASTREADOR (SCRAPER) ---
    async def _extrair_e_salvar(self, session, nome, url):
        """Acessa a Wiki, extrai, traduz e persiste os dados."""
        async with session.get(url) as resp:
            if resp.status != 200: return False
            
            soup = BeautifulSoup(await resp.text(), 'html.parser')
            content = soup.find('div', {'class': 'mw-parser-output'})
            if not content: return False

            # Captura Lore (H2 e P)
            lore_raw = ""
            for el in content.find_all(['h2', 'p'], recursive=False)[:8]:
                if len(el.text.strip()) > 30: lore_raw += el.text.strip() + "\n\n"

            # Captura Infobox
            detalhes_raw = []
            img_url = None
            infobox = soup.find('aside', {'class': 'portable-infobox'})
            if infobox:
                img_tag = infobox.find('img', {'class': 'pi-image-thumbnail'})
                if img_tag: img_url = img_tag.get('src')
                for item in infobox.find_all('div', {'class': 'pi-item pi-data'}):
                    l = item.find('h3').text.strip()
                    v = item.find('div', {'class': 'pi-data-value'}).text.strip()
                    detalhes_raw.append(f"{l}: {v}")

            # Tradução e Limpeza
            lore_pt = self._sanitizar_texto(self.translator.translate(lore_raw[:1200]))
            detalhes_pt = self._sanitizar_texto(self.translator.translate("\n".join(detalhes_raw)))

            with sqlite3.connect(DB_PATH) as conn:
                conn.cursor().execute('''
                    INSERT OR REPLACE INTO criaturas (nome, descricao, fraquezas, imagem_url) 
                    VALUES (?, ?, ?, ?)
                ''', (nome, lore_pt, detalhes_pt, img_url))
                conn.commit()
            return True

    @app_commands.command(name="alimentar_bestiario", description="⚙️ Importação em massa da Wiki")
    async def alimentar_bestiario(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔍 Iniciando rastreamento...")
        cat_url = f"{WITCHER_WIKI_URL}/wiki/Category:The_Witcher_3_bestiary"

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(cat_url) as resp:
                if resp.status != 200: return await interaction.edit_original_response(content="❌ Falha na Wiki.")
                
                soup = BeautifulSoup(await resp.text(), 'html.parser')
                links = [(a.text.strip(), WITCHER_WIKI_URL + a.get('href')) 
                         for a in soup.select('.category-page__member-link')]

                for i, (nome, url) in enumerate(links, 1):
                    await self._extrair_e_salvar(session, nome, url)
                    if i % 3 == 0:
                        await interaction.edit_original_response(content=f"🔄 Progresso: {i}/{len(links)}")
                    await asyncio.sleep(1.5) # Respeito ao servidor

        await interaction.edit_original_response(content="✅ Bestiário alimentado e traduzido!")

async def setup(bot):
    await bot.add_cog(Bestiary(bot))