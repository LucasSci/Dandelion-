import asyncio
import os
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from openai import AsyncOpenAI

from config import settings

API_KEY = os.getenv("OPENAI_API_KEY")
_STOPWORDS = frozenset(
    {
        "de",
        "da",
        "do",
        "dos",
        "das",
        "a",
        "o",
        "as",
        "os",
        "em",
        "no",
        "na",
        "que",
        "quem",
        "qual",
        "quando",
        "onde",
        "como",
        "por",
        "para",
        "com",
    }
)
_DIGITS_ONLY = re.compile(r"\D+")

class AIHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        self.gemini_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
        self._skip_teste_gerar_prompt = self.bot.tree.get_command("teste_gerar_prompt") is not None
        if self._skip_teste_gerar_prompt:
            self.__cog_app_commands__ = [
                command
                for command in self.__cog_app_commands__
                if command.name != "teste_gerar_prompt"
            ]
        if API_KEY:
            try:
                self.client = AsyncOpenAI(api_key=API_KEY)
                print("✅ OpenAI (ChatGPT) conectada!")
            except Exception as e:
                print(f"❌ Erro ao conectar OpenAI: {e}")

    def _split_discord_message(self, text: str, limit: int = 2000) -> list[str]:
        if len(text) <= limit:
            return [text]
        return [text[i : i + limit] for i in range(0, len(text), limit)]

    def safe_int(self, text: str) -> int:
        """Converte texto em int de forma segura, retornando 0 se falhar"""
        try:
            # Filtra apenas os dígitos da string (ex: '500 moedas' -> '500')
            if not text:
                return 0
            digits = _DIGITS_ONLY.sub("", text)
            return int(digits) if digits else 0
        except ValueError:
            return 0

    def _extrair_keywords(self, texto: str) -> list[str]:
        tokens = re.findall(r"\w+", texto.lower())
        filtradas = [t for t in tokens if t not in _STOPWORDS and len(t) > 3]
        return filtradas[:6]

    def _lore_visibility_clause(self, is_mestre: bool) -> str:
        if is_mestre:
            return ""
        return " AND (is_private = 0 OR is_private IS NULL OR owner_id = ?)"

    async def buscar_contexto_rag(self, pergunta: str, user_id: int | None = None, is_mestre: bool = True) -> str:
        """Busca fatos relevantes em lore e NPCs para enriquecer a resposta."""
        termos = self._extrair_keywords(pergunta)
        if not termos:
            return ""

        likes = " OR ".join(["titulo LIKE ? OR resumo LIKE ? OR conteudo LIKE ?"] * len(termos))
        params = []
        for termo in termos:
            like = f"%{termo}%"
            params.extend([like, like, like])
        visibility_clause = self._lore_visibility_clause(is_mestre)
        if visibility_clause:
            params.append(user_id)

        privacy_filter = "is_private = 0"
        if user_id is not None:
            privacy_filter = "is_private = 0 OR owner_id = ?"
            params.append(user_id)

        async with self.bot.db.execute(
            f"""
            SELECT titulo, resumo, conteudo
            FROM lore_entries
            WHERE {likes}{visibility_clause}
            ORDER BY atualizado_em DESC
            LIMIT 5
        """

        async with self.bot.db.execute(lore_query, params) as cursor:
            lore_rows = await cursor.fetchall()

        npc_likes = " OR ".join(
            ["nome LIKE ? OR personalidade LIKE ? OR humor LIKE ? OR habitos LIKE ? OR observacoes LIKE ?"] * len(termos)
        )
        npc_params = []
        for termo in termos:
            like = f"%{termo}%"
            npc_params.extend([like, like, like, like, like])

        async with self.bot.db.execute(
            f"""
            SELECT nome, personalidade, humor, observacoes
            FROM npc_profiles
            WHERE {npc_likes}
            ORDER BY nome
            LIMIT 5
            """,
            npc_params,
        ) as cursor:
            npc_rows = await cursor.fetchall()

        partes = []
        if lore_rows:
            lore_txt = []
            for titulo, resumo, conteudo in lore_rows:
                base = (resumo or conteudo or "").strip()
                if len(base) > 200:
                    base = f"{base[:200]}..."
                lore_txt.append(f"- {titulo}: {base}")
            partes.append("LORE RELEVANTE:\n" + "\n".join(lore_txt))

        if npc_rows:
            npc_txt = []
            for nome, personalidade, humor, observacoes in npc_rows:
                obs = observacoes or ""
                if len(obs) > 120:
                    obs = f"{obs[:120]}..."
                npc_txt.append(
                    f"- {nome}: {personalidade} | Humor: {humor} | {obs}".strip()
                )
            partes.append("NPCS & RUMORES:\n" + "\n".join(npc_txt))

        return "\n\n".join(partes)

    async def ler_cronologia_estrita(self):
        """Lê TODOS os eventos na ordem correta"""
        async with self.bot.db.execute("SELECT id, conteudo FROM memoria_campanha ORDER BY id ASC") as c:
            rows = await c.fetchall()
        
        if not rows:
            return "INÍCIO DA AVENTURA. Nenhum evento ocorreu ainda."

        return "\n".join(f"- {conteudo}" for _, conteudo in rows)

    async def ler_lore_mundo(self, user_id: int | None = None, is_mestre: bool = True) -> str:
        """Lê todo o lore inserido pelo mestre para servir de base ao mundo."""
        params = []
        query = "SELECT titulo, resumo, conteudo FROM lore_entries"
        if not is_mestre:
            query += " WHERE is_private = 0 OR is_private IS NULL OR owner_id = ?"
            params.append(user_id)
        query += " ORDER BY id ASC"
        async with self.bot.db.execute(query, params) as c:
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
        if not self.client:
            return None
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
        except Exception as e:
            print(f"Erro IA gerar imagem: {e}")
            return None

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

    async def gerar_narrativa_combate(
        self,
        atacante: str,
        alvo: str,
        arma: str,
        dano: int,
        contexto: str | None = None,
    ) -> str:
        if not self.client:
            return ""
        prompt = (
            "Você é um narrador de combate em um RPG estilo The Witcher.\n"
            f"Atacante: {atacante}\n"
            f"Alvo: {alvo}\n"
            f"Arma/Técnica: {arma}\n"
            f"Dano causado: {dano}\n"
        )
        if contexto:
            prompt += f"Contexto adicional: {contexto}\n"
        prompt += "Crie uma frase curta e visceral descrevendo o golpe e seu impacto."

        try:
            r = await self.client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"Erro IA narrativa combate: {e}")
            return ""
        
    async def get_response(self, prompt: str) -> str:
        """Chat genérico"""
        if not self.client:
            return "IA Off."
        try:
            r = await self.client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}]
            )
            return r.choices[0].message.content or ""
        except Exception as e:
            print(f"Erro IA resposta: {e}")
            return "Erro."

    async def gerar_descricao_item(self, nome, tipo):
        return await self.get_response(f"Descreva o item '{nome}' ({tipo}) para RPG The Witcher. Curto.")

    async def gerar_item_aleatorio(self, raridade):
        raw = await self.get_response(f"Gere um item {raridade} formato: NOME|TIPO|EFEITO")
        if not raw:
            return None
        p = [segment.strip() for segment in raw.split("|")]
        return {"nome": p[0], "tipo": p[1], "efeito": p[2]} if len(p) >= 3 else None

    @app_commands.command(name="teste_gerar_prompt", description="[DEV] Gera um prompt de imagem baseado em uma URL")
    @app_commands.describe(url_imagem="A URL da imagem de referência da Fandom")
    async def teste_gerar_prompt(self, interaction: discord.Interaction, url_imagem: str):
        await interaction.response.defer()

        if not self.gemini_client:
            return await interaction.followup.send("❌ Gemini API não configurada.")
        if not self.bot.http_session:
            return await interaction.followup.send("❌ Sessão HTTP indisponível.")

        try:
            async with self.bot.http_session.get(url_imagem) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Não consegui acessar a imagem na URL fornecida.")
                image_data = await resp.read()

            prompt_text = """
            Analise esta imagem de uma criatura.
            Crie um prompt de geração de imagem (text-to-image) altamente detalhado para recriar esta criatura.
            O estilo deve ser: "Dark fantasy RPG concept art, estilo The Witcher 3, alta resolução, 8k, texturas realistas, iluminação dramática".
            Descreva a anatomia, a pose, as texturas da pele/pelo e o ambiente com base na imagem de referência.
            Retorne APENAS o prompt em inglês.
            """

            contents = [
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt_text),
                        types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                    ]
                )
            ]

            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model="gemini-2.0-flash",
                contents=contents,
            )

            prompt_gerado = response.text

            embed = discord.Embed(
                title="🎨 Prompt Gerado pelo Gemini",
                description=prompt_gerado[:4000],
                color=0x00FF00,
            )
            embed.set_thumbnail(url=url_imagem)
            embed.set_footer(text="Copie este prompt e use no Midjourney/Leonardo.ai")

            await interaction.followup.send(embed=embed)
        except Exception:
            print("Falha no comando teste_gerar_prompt")
            await interaction.followup.send("❌ Erro na análise da IA. Consulte os logs.")

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
        is_mestre = getattr(interaction.user.guild_permissions, "administrator", False)
        lore = await self.ler_lore_mundo(interaction.user.id, is_mestre=is_mestre)
        rag = await self.buscar_contexto_rag(solicitacao, interaction.user.id, is_mestre=is_mestre)
        prompt = (
            "Você é Dandelion, o bardo narrador de The Witcher.\n"
            "Use a cronologia e o lore abaixo como contexto real.\n\n"
            f"CRONOLOGIA:\n{cronologia}\n\n"
            f"LORE:\n{lore}\n\n"
            f"CONTEXTO ENCONTRADO (RAG):\n{rag or 'Nenhuma entrada relevante encontrada.'}\n\n"
            f"SOLICITAÇÃO DO MESTRE/JOGADOR:\n{solicitacao}\n\n"
            "Responda em português brasileiro, com narrativa evocativa e objetiva."
        )

        resposta = await self.get_response(prompt)
        for chunk in self._split_discord_message(resposta):
            await interaction.followup.send(chunk)

async def setup(bot):
    await bot.add_cog(AIHandler(bot))
