import discord
from discord.ext import commands
from openai import AsyncOpenAI
import os

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
        """Converte texto em int de forma segura, retornando 0 se falhar"""
        try:
            # Filtra apenas os dígitos da string (ex: '500 moedas' -> '500')
            digits = ''.join(filter(str.isdigit, text))
            return int(digits) if digits else 0
        except:
            return 0

    async def ler_cronologia_estrita(self):
        """Lê TODOS os eventos na ordem correta"""
        async with self.bot.db.execute("SELECT id, conteudo FROM memoria_campanha ORDER BY id ASC") as c:
            rows = await c.fetchall()
        
        if not rows: return "INÍCIO DA AVENTURA. Nenhum evento ocorreu ainda."
        
        texto = ""
        for r in rows:
            texto += f"- {r[1]}\n"
        return texto

    async def gerar_quest_cronologica(self, dificuldade: str) -> dict:
        if not self.client: return None
        
        cronologia = await self.ler_cronologia_estrita()
        
        prompt = (
            f"Atue como Mestre de RPG (The Witcher/Zerrikania).\n"
            f"=== LINHA DO TEMPO (FATOS REAIS) ===\n"
            f"{cronologia}\n"
            f"====================================\n\n"
            
            f"TAREFA: Crie um CONTRATO (Dificuldade {dificuldade}) que seja uma consequência LÓGICA dos eventos acima.\n"
            f"IMPORTANTE: Você deve explicar qual evento específico do passado motivou esta missão.\n\n"
            
            f"FORMATO DE RESPOSTA (Obrigatório, separado por '|'):\n"
            f"TÍTULO | DESCRIÇÃO | OURO (apenas numeros) | XP (apenas numeros) | CLASSES | REGIÃO | MONSTRO | PROMPT VISUAL | JUSTIFICATIVA"
        )

        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user", "content":prompt}],
                temperature=0.7
            )
            
            raw = resp.choices[0].message.content.strip().replace("```", "")
            parts = raw.split('|')
            
            # Garante que temos pelo menos os campos essenciais
            if len(parts) >= 8:
                # Se faltar a nota (índice 8), cria uma padrão
                nota = parts[8].strip() if len(parts) > 8 else "Sem justificativa gerada."
                
                return {
                    "titulo": parts[0].strip(),
                    "descricao": parts[1].strip(),
                    "ouro": self.safe_int(parts[2]), # <--- CORREÇÃO AQUI
                    "xp": self.safe_int(parts[3]),   # <--- CORREÇÃO AQUI
                    "classes": parts[4].strip(),
                    "regiao": parts[5].strip(),
                    "monstro": parts[6].strip(),
                    "prompt_img": parts[7].strip(),
                    "nota_mestre": nota
                }
            return None
        except Exception as e:
            print(f"Erro IA: {e}")
            return None

    async def gerar_imagem_dalle(self, prompt_visual: str):
        if not self.client: return None
        try:
            p = f"The Witcher RPG art style. {prompt_visual}"
            r = await self.client.images.generate(model="dall-e-3", prompt=p, size="1024x1024", quality="standard", n=1)
            return r.data[0].url
        except: return None
        
    async def get_response(self, prompt: str) -> str:
        """Chat genérico"""
        if not self.client: return "IA Off."
        try:
            r = await self.client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}]
            )
            return r.choices[0].message.content
        except: return "Erro."

    async def gerar_descricao_item(self, nome, tipo):
        return await self.get_response(f"Descreva o item '{nome}' ({tipo}) para RPG The Witcher. Curto.")

    async def gerar_item_aleatorio(self, raridade):
        raw = await self.get_response(f"Gere um item {raridade} formato: NOME|TIPO|EFEITO")
        p = raw.split('|')
        return {"nome": p[0], "tipo": p[1], "efeito": p[2]} if len(p)>=3 else None

async def setup(bot):
    await bot.add_cog(AIHandler(bot))