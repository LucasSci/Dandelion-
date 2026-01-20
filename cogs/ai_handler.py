import discord
from discord import app_commands
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

    async def ler_lore_mundo(self) -> str:
        """Lê todo o lore inserido pelo mestre para servir de base ao mundo."""
        async with self.bot.db.execute(
            "SELECT titulo, resumo, conteudo FROM lore_entries ORDER BY id ASC"
        ) as c:
            rows = await c.fetchall()

        if not rows:
            return "LORE VAZIO. Nenhuma informação adicional do mundo foi registrada."

        linhas = []
        for titulo, resumo, conteudo in rows:
            base = resumo or conteudo or ""
            base = base.strip()
            if len(base) > 240:
                base = f"{base[:240]}..."
            linhas.append(f"- {titulo}: {base}")

        return "\n".join(linhas)

    async def gerar_quest_cronologica(self, dificuldade: str, regiao: str = None) -> dict:
        if not self.client: return None
        
        cronologia = await self.ler_cronologia_estrita()
        lore = await self.ler_lore_mundo()

        regiao_info = (
            f"REGIÃO ESCOLHIDA PELO MESTRE: {regiao}. A missão deve acontecer exatamente nesta região.\n"
            if regiao
            else "REGIÃO: escolha a região mais coerente com a cronologia e o lore.\n"
        )
        
        prompt = (
            f"Atue como Mestre de RPG (The Witcher/Zerrikania).\n"
            f"=== LINHA DO TEMPO (FATOS REAIS) ===\n"
            f"{cronologia}\n"
            f"====================================\n\n"
            f"=== LORE DO MUNDO (FATOS REAIS) ===\n"
            f"{lore}\n"
            f"===================================\n\n"
            f"{regiao_info}\n"
            
            f"TAREFA: Crie um CONTRATO (Dificuldade {dificuldade}) que seja uma consequência LÓGICA dos eventos acima e do lore.\n"
            f"ESTILO: Misture o senso investigativo e moral cinzento de The Witcher, a sensação de rivalidade e escalada de ameaça de Sombras de Mordor, e a exploração/descoberta de Skyrim.\n"
            f"FOCO: A missão precisa fazer sentido dentro do universo de The Witcher e na região escolhida.\n"
            f"IMPORTANTE: Você deve explicar qual evento específico do passado motivou esta missão e quais fatos do lore foram usados.\n"
            f"GANCHOS: A descrição deve terminar com uma linha 'Gancho futuro: ...' conectando a missão a um próximo arco.\n\n"
            f"LINGUAGEM: escreva tudo em português brasileiro.\n\n"
            
            f"FORMATO DE RESPOSTA (Obrigatório, separado por '|'):\n"
            f"TÍTULO | DESCRIÇÃO | OURO (apenas numeros) | XP (apenas numeros) | CLASSES | REGIÃO | MONSTRO | PROMPT VISUAL (em português brasileiro e sem texto na imagem) | JUSTIFICATIVA"
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
            p = (
                "The Witcher RPG art style. "
                f"{prompt_visual}. "
                "Sem texto, sem letras, sem palavras, sem marcas d'água."
            )
            r = await self.client.images.generate(
                model="dall-e-3",
                prompt=p,
                size="1024x1024",
                quality="hd",
                n=1,
            )
            return r.data[0].url
        except: return None

    async def gerar_dialogo_npc(self, npc: dict, mensagem: str) -> str:
        if not self.client:
            return "⚠️ A IA não está configurada para diálogos no momento."

        nome = npc.get("nome", "NPC")
        personalidade = npc.get("personalidade", "neutro")
        humor = npc.get("humor", "equilibrado")
        habitos = npc.get("habitos", "")
        observacoes = npc.get("observacoes", "")

        prompt = (
            "Você é um NPC em um RPG estilo The Witcher.\n"
            f"Nome: {nome}\n"
            f"Personalidade: {personalidade}\n"
            f"Humor: {humor}\n"
            f"Hábitos: {habitos}\n"
            f"Observações: {observacoes}\n"
            "Responda ao jogador mantendo o estilo do NPC, com frases curtas e expressivas.\n"
            "Evite sair do personagem.\n"
            f"Jogador diz: {mensagem}\n"
            "Resposta do NPC:"
        )

        try:
            r = await self.client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"Erro IA diálogo NPC: {e}")
            return "⚠️ Não consegui gerar a resposta do NPC."
        
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

    @app_commands.command(
        name="dandelion",
        description="🧠 Pede ao narrador IA para descrever uma cena ou consequência.",
    )
    @app_commands.describe(solicitacao="O que aconteceu ou o que você quer narrar?")
    async def dandelion(self, interaction: discord.Interaction, solicitacao: str):
        await interaction.response.defer()
        if not self.client:
            return await interaction.followup.send("❌ IA não configurada no momento.")

        cronologia = await self.ler_cronologia_estrita()
        lore = await self.ler_lore_mundo()
        prompt = (
            "Você é Dandelion, o bardo narrador de The Witcher.\n"
            "Use a cronologia e o lore abaixo como contexto real.\n\n"
            f"CRONOLOGIA:\n{cronologia}\n\n"
            f"LORE:\n{lore}\n\n"
            f"SOLICITAÇÃO DO MESTRE/JOGADOR:\n{solicitacao}\n\n"
            "Responda em português brasileiro, com narrativa evocativa e objetiva."
        )

        resposta = await self.get_response(prompt)
        await interaction.followup.send(resposta)

async def setup(bot):
    await bot.add_cog(AIHandler(bot))
