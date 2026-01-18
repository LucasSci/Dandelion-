import discord
from discord.ext import commands
from openai import AsyncOpenAI
import os
import random
import asyncio
import logging

log = logging.getLogger(__name__)
API_KEY = os.getenv("OPENAI_API_KEY")

class AIHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        if API_KEY:
            try:
                self.client = AsyncOpenAI(api_key=API_KEY)
                print("✅ OpenAI (ChatGPT) conectada!")
            except Exception as e:
                print(f"❌ Erro ao conectar OpenAI: {e}")

    def safe_int(self, text: str) -> int:
        try:
            digits = ''.join(filter(str.isdigit, text))
            return int(digits) if digits else 0
        except: return 0

    async def gerar_quest_imersiva(self, regiao_atual: str, coordenadas: tuple) -> dict:
        """
        Gera uma missão estritamente baseada na geografia e cultura do local.
        """
        if not self.client: return None
        
        # 1. Buscar Contexto Geográfico Rico do Banco
        lore_geo = "Região desconhecida. Improvise com base em The Witcher."
        lenda_local = "Sem lendas conhecidas."
        
        try:
            async with self.bot.db.execute(
                "SELECT descricao_lore, lendas_locais FROM locais_mundo WHERE nome LIKE ?", 
                (f'%{regiao_atual}%',)
            ) as c:
                res = await c.fetchone()
                if res:
                    lore_geo = res[0] # Aqui está o texto rico (Clima, Cultura, Geografia)
                    lenda_local = res[1]
        except Exception as e:
            log.error(f"Erro ao buscar lore: {e}")

        # 2. Construção do Prompt Reforçado
        prompt = (
            f"Atue como Mestre de RPG especialista em The Witcher.\n"
            f"--- DADOS DA REGIÃO: {regiao_atual} ---\n"
            f"{lore_geo}\n"
            f"LENDA LOCAL: {lenda_local}\n"
            f"--------------------------------------\n\n"
            
            f"TAREFA: Crie um CONTRATO (Quest) que faça sentido ESTRITAMENTE para esta região.\n"
            f"REGRAS DE IMERSÃO (CRÍTICO):\n"
            f"1. NÃO crie biomas errados (Ex: Nada de pântanos em desertos, nada de gelo em selvas).\n"
            f"2. Use os problemas culturais citados acima (Ex: Se for Velen, use guerra/fome; Se for Zerrikania, use calor/dragões).\n"
            f"3. O monstro deve ser nativo deste clima.\n\n"
            
            f"FORMATO DE RESPOSTA (Separado por '|'):\n"
            f"TÍTULO | DESCRIÇÃO (Max 300 chars, cite o clima/ambiente) | OURO (Int) | XP (Int) | CLASSES | MONSTRO_PRINCIPAL"
        )

        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user", "content":prompt}],
                temperature=0.7 # Temperatura menor para respeitar mais as regras
            )
            
            raw = resp.choices[0].message.content.strip()
            parts = raw.split('|')
            
            if len(parts) >= 6:
                return {
                    "titulo": parts[0].strip(),
                    "descricao": parts[1].strip(),
                    "ouro": self.safe_int(parts[2]),
                    "xp": self.safe_int(parts[3]),
                    "classes": parts[4].strip(),
                    "monstro": parts[5].strip(),
                    "regiao": regiao_atual
                }
            return None

        except Exception as e:
            log.error(f"Erro IA Imersiva: {e}")
            return None

    # (Mantenha outras funções auxiliares se houver, como gerar_imagem_dalle)

async def setup(bot):
    await bot.add_cog(AIHandler(bot))