import discord
import random
import asyncio
import io
from typing import Optional
from discord.ext import commands
from discord import app_commands
from data_cache import get_world_location_names
from ui.combat_view import CombateView, MestreView, Roll20LinkView
from utils import gerar_barra
from vtt_engine.grid_system import GridMap
from utils import rolar_dados
from config import settings

DB_NAME = "bestiario.db"
DEFAULT_MONSTER_HP = 50
DEFAULT_MONSTER_INI = 10
DEFAULT_MONSTER_DANO = "1d6"
MAP_WIDTH = 12
MAP_HEIGHT = 8
TERRAIN_EMOJI = {
    0: "🟩",
    1: "🟥",
    2: "🟫",
}
STATUS_EFFECTS = {
    "Sangrando": {"dano": 2, "duracao": 3, "descricao": "Perde vida no início do turno."},
}

# --- HELPER: SISTEMA DE XP ---
async def aplicar_xp(db, user_id, xp_ganho, channel):
    """Calcula XP, verifica Level Up e atualiza o banco."""
    async with db.execute("SELECT nivel, xp_atual, hp_max, ataque FROM personagens WHERE user_id = ?", (user_id,)) as cursor:
        dados = await cursor.fetchone()
    
    if not dados: return
    nivel, xp, hp, atk = dados
    
    # Fórmula: Nível * 1000 de XP necessário para o próximo
    xp_prox_nivel = nivel * 1000 
    novo_xp = xp + xp_ganho
    msg = ""

    if novo_xp >= xp_prox_nivel:
        novo_nivel = nivel + 1
        novo_xp = novo_xp - xp_prox_nivel
        
        # Bônus de Level Up
        novo_hp = hp + 5   # +5 de Vida
        novo_atk = atk + 1 # +1 de Ataque
        
        await db.execute("""
            UPDATE personagens 
            SET nivel=?, xp_atual=?, hp_max=?, ataque=? 
            WHERE user_id=?""", 
            (novo_nivel, novo_xp, novo_hp, novo_atk, user_id))
            
        msg = f"\n🎉 **LEVEL UP!** Você alcançou o nível **{novo_nivel}**! (+5 HP, +1 ATK)"
    else:
        await db.execute("UPDATE personagens SET xp_atual=? WHERE user_id=?", (novo_xp, user_id))
    
    await db.commit()
    if msg: await channel.send(f"<@{user_id}> {msg}")

# --- CLASSE DE COMBATE ---
class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    # Método movido para DENTRO da classe (Correção Importante)
    def obter_resumo_combate(self, channel_id):
        session = self.sessions.get(channel_id)
        if not session: return "Nenhum combate ocorrendo."
        
        monstros_str = ", ".join(
            [f"{m['nome']} (HP:{m['hp_atual']}/{m['hp_max']})" for m in session['monstros']]
        ) or "Nenhum"
        jogadores_str = ", ".join([f"{p['nome']} (HP:{p['hp']})" for p in session['jogadores']]) or "Nenhum"
        
        return f"""
        CENÁRIO ATUAL:
        Região: {session.get('regiao', 'Desconhecida')}
        Inimigos: {monstros_str}
        Heróis: {jogadores_str}.
        """

    async def ac_criatura(self, interaction: discord.Interaction, current: str):
        termo = current.strip()
        if not termo:
            async with self.bot.db.execute(
                """
                SELECT nome FROM (
                    SELECT nome AS nome FROM criaturas
                    UNION
                    SELECT name AS nome FROM monsters
                )
                ORDER BY nome COLLATE NOCASE LIMIT 25
                """
            ) as cursor:
                rows = await cursor.fetchall()
            return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]
        async with self.bot.db.execute(
            """
            SELECT nome AS nome FROM criaturas WHERE nome LIKE ? COLLATE NOCASE
            UNION
            SELECT name AS nome FROM monsters WHERE name LIKE ? COLLATE NOCASE
            ORDER BY nome COLLATE NOCASE LIMIT 25
            """,
            (f"{termo}%", f"{termo}%"),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]

    async def regiao_autocomplete(self, interaction: discord.Interaction, current: str):
        nomes = await get_world_location_names(self.bot.db)
        termo = current.strip().lower()
        if termo:
            nomes = [nome for nome in nomes if termo in nome.lower()]
        return [app_commands.Choice(name=nome, value=nome) for nome in nomes[:25]]

    async def _buscar_criatura(self, nome: str):
        async with self.bot.db.execute(
            "SELECT nome, hp_max, imagem_url, iniciativa, dano_base FROM criaturas WHERE nome LIKE ? ORDER BY nome LIMIT 1",
            (f"%{nome}%",),
        ) as cursor:
            criatura = await cursor.fetchone()
        if criatura:
            return criatura
        async with self.bot.db.execute(
            "SELECT name, threat_level FROM monsters WHERE name LIKE ? ORDER BY name LIMIT 1",
            (f"%{nome}%",),
        ) as cursor:
            monstro = await cursor.fetchone()
        if not monstro:
            return None
        nome_monstro, _threat_level = monstro
        return (
            nome_monstro,
            DEFAULT_MONSTER_HP,
            None,
            DEFAULT_MONSTER_INI,
            DEFAULT_MONSTER_DANO,
        )

    def _proximo_indice_monstro(self, session, nome_base):
        existentes = [m for m in session["monstros"] if m["nome_base"] == nome_base]
        return len(existentes) + 1

    def _status_key(self, alvo: dict) -> str:
        if alvo["tipo"] == "MONSTRO":
            return f"monstro:{alvo.get('monstro_id')}"
        return f"jogador:{alvo.get('user_id')}"

    async def _emitir_evento_vtt(self, evento: str, payload: dict) -> None:
        if not settings.vtt_api_url or not self.bot.http_session:
            return
        url = settings.vtt_api_url.rstrip("/") + "/vtt/event"
        try:
            async with self.bot.http_session.post(
                url, json={"event_type": evento, "payload": payload}
            ) as resp:
                resp.release()
        except Exception:
            return

    def _gerar_ordem_iniciativa(self, session):
        ordem = []
        log_iniciativa = []
        for p in session["jogadores"]:
            if p["hp"] <= 0:
                continue
            roll = random.randint(1, 20)
            ordem.append({**p, "tipo": "JOGADOR", "roll": roll})
            log_iniciativa.append(f"{p['nome']}: 🎲 {roll}")

        for monstro in session["monstros"]:
            if monstro["hp_atual"] <= 0:
                continue
            roll_monstro = random.randint(1, 20) + (monstro["ini"] or 0)
            ordem.append(
                {
                    "tipo": "MONSTRO",
                    "nome": monstro["nome"],
                    "monstro_id": monstro["id"],
                    "roll": roll_monstro,
                }
            )
            log_iniciativa.append(f"{monstro['nome']}: 🎲 {roll_monstro}")

        ordem.sort(key=lambda x: x["roll"], reverse=True)
        return ordem, log_iniciativa

    async def _aplicar_status_inicio_turno(self, session, atual):
        key = self._status_key(atual)
        efeitos = session["status_effects"].get(key, [])
        if not efeitos:
            return
        total_dano = 0
        mensagens = []
        for efeito in efeitos:
            dano = efeito.get("dano", 0)
            if dano:
                total_dano += dano
            efeito["duracao"] -= 1
            mensagens.append(f"{efeito['nome']} ({max(0, efeito['duracao'])} turnos)")

        if atual["tipo"] == "MONSTRO":
            monstro = self._obter_monstro(session, atual.get("monstro_id"))
            if monstro:
                monstro["hp_atual"] -= total_dano
        else:
            jogador = next(
                (p for p in session["jogadores"] if p["user_id"] == atual["user_id"]),
                None,
            )
            if jogador:
                jogador["hp"] -= total_dano
                for p in session["ordem"]:
                    if p.get("user_id") == jogador["user_id"]:
                        p["hp"] = jogador["hp"]

        efeitos[:] = [e for e in efeitos if e["duracao"] > 0]
        if mensagens and total_dano > 0:
            session["log"].append(
                f"🩸 {atual.get('nome', 'Alvo')} sofre efeitos: {', '.join(mensagens)} (-{total_dano} HP)"
            )

        if not efeitos:
            session["status_effects"].pop(key, None)

        if atual["tipo"] == "MONSTRO":
            monstro = self._obter_monstro(session, atual.get("monstro_id"))
            if monstro and monstro["hp_atual"] <= 0:
                session["log"].append(f"💀 {monstro['nome']} sucumbiu aos efeitos!")
        else:
            jogador = next(
                (p for p in session["jogadores"] if p["user_id"] == atual["user_id"]),
                None,
            )
            if jogador and jogador["hp"] <= 0:
                session["log"].append(f"💀 {jogador['nome']} caiu pelos efeitos!")

    def _criar_instancia_monstro(self, session, nome, hp, img, ini, dano_base):
        session["contador_monstros"] += 1
        indice = self._proximo_indice_monstro(session, nome)
        nome_exibicao = f"{nome} #{indice}" if indice > 1 else nome
        return {
            "id": session["contador_monstros"],
            "nome_base": nome,
            "nome": nome_exibicao,
            "hp_max": hp,
            "hp_atual": hp,
            "img": img,
            "ini": ini,
            "dano_base": dano_base,
        }

    def _monstros_vivos(self, session):
        return [m for m in session["monstros"] if m["hp_atual"] > 0]

    def _obter_monstro(self, session, monstro_id):
        return next((m for m in session["monstros"] if m["id"] == monstro_id), None)

    def _formatar_monstros(self, session, atual):
        if not session["monstros"]:
            return "Sem inimigos adicionados ainda.\n"

        linhas = []
        for m in session["monstros"]:
            status = "💀 CAÍDO" if m["hp_atual"] <= 0 else f"{m['hp_atual']}/{m['hp_max']}"
            icone = "👉" if (atual["tipo"] == "MONSTRO" and atual.get("monstro_id") == m["id"]) else "👹"
            barra = gerar_barra(m["hp_atual"], m["hp_max"])
            linhas.append(f"{icone} **{m['nome']}**\n{barra} `{status}`")
        return "\n".join(linhas) + "\n"

    def _resolver_bioma(self, regiao: str | None) -> str:
        if not regiao:
            return "Planície"
        regiao_lower = regiao.lower()
        if "pântano" in regiao_lower or "pantano" in regiao_lower:
            return "Pântano"
        if "floresta" in regiao_lower or "bosque" in regiao_lower:
            return "Floresta"
        if "caverna" in regiao_lower or "gruta" in regiao_lower:
            return "Caverna"
        if "cidade" in regiao_lower or "vila" in regiao_lower or "vilarejo" in regiao_lower:
            return "Cidade"
        return "Planície"

    def _renderizar_battlemap(self, grid):
        linhas = []
        for row in grid:
            linhas.append("".join(TERRAIN_EMOJI.get(cell, "⬜") for cell in row))
        return "\n".join(linhas)

    async def _enviar_battlemap(self, channel, session):
        if session.get("battlemap_enviado"):
            return
        bioma = self._resolver_bioma(session.get("regiao"))
        grid_map = GridMap(width=MAP_WIDTH, height=MAP_HEIGHT)
        grid_map.generate(biome=bioma)
        mapa = self._renderizar_battlemap(grid_map.grid)
        descricao = (
            f"**Bioma:** {bioma}\n"
            f"{mapa}\n"
            "🟩 livre • 🟥 bloqueado • 🟫 difícil"
        )
        embed = discord.Embed(title="🗺️ Tabletop", description=descricao, color=0x1f8b4c)
        view = None
        if settings.roll20_campaign_url:
            view = Roll20LinkView(settings.roll20_campaign_url)
        await channel.send(embed=embed, view=view)
        session["battlemap_enviado"] = True

    @app_commands.command(name="combate_criar", description="Cria uma sala de batalha")
    @app_commands.describe(regiao="Região do combate", monstro_nome="Criatura opcional do bestiário")
    @app_commands.autocomplete(monstro_nome=ac_criatura, regiao=regiao_autocomplete)
    async def combate_criar(self, interaction: discord.Interaction, regiao: str, monstro_nome: Optional[str] = None):
        if interaction.channel_id in self.sessions:
            return await interaction.response.send_message("❌ Já existe um combate neste canal.", ephemeral=True)

        self.sessions[interaction.channel_id] = {
            'status': 'LOBBY',
            'bloqueado': False,
            'mensagem_id': None, # ID da mensagem para edição
            'regiao': regiao,
            'monstros': [],
            'jogadores': [],
            'ordem': [],
            'turno_index': 0,
            'turno_monstro': False,
            'log': [f"Combate iniciado em {regiao}."],
            'contador_monstros': 0,
            'battlemap_enviado': False,
            'status_effects': {},
            'round': 1,
        }
        session = self.sessions[interaction.channel_id]

        if monstro_nome:
            monster_data = await self._buscar_criatura(monstro_nome)
            if not monster_data:
                return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)
            nome, hp, img, ini, dano_base = monster_data
            session["monstros"].append(self._criar_instancia_monstro(session, nome, hp, img, ini, dano_base))
            session["log"].append(f"Um {nome} selvagem apareceu!")

        titulo = f"⚠️ COMBATE: {regiao}"
        desc = "**Aguardando guerreiros...**\n\n"
        desc += self._formatar_monstros(session, {"tipo": "MONSTRO"})
        embed = discord.Embed(title=titulo, description=desc, color=0xFF0000)
        if session["monstros"]:
            img = session["monstros"][0]["img"]
            if img:
                embed.set_image(url=img)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="combate_adicionar", description="Adiciona criaturas ao combate")
    @app_commands.describe(monstro_nome="Criatura do bestiário", quantidade="Quantidade")
    @app_commands.autocomplete(monstro_nome=ac_criatura)
    async def combate_adicionar(self, interaction: discord.Interaction, monstro_nome: str, quantidade: int = 1):
        session = self.sessions.get(interaction.channel_id)
        if not session:
            return await interaction.response.send_message("❌ Nenhum combate criado neste canal.", ephemeral=True)
        if session["status"] != "LOBBY":
            return await interaction.response.send_message("❌ Só é possível adicionar criaturas antes do combate iniciar.", ephemeral=True)
        if quantidade < 1 or quantidade > 10:
            return await interaction.response.send_message("❌ Quantidade inválida (1-10).", ephemeral=True)

        monster_data = await self._buscar_criatura(monstro_nome)
        if not monster_data:
            return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)

        nome, hp, img, ini, dano_base = monster_data
        for _ in range(quantidade):
            session["monstros"].append(self._criar_instancia_monstro(session, nome, hp, img, ini, dano_base))
        session["log"].append(f"{quantidade}x {nome} adicionado ao combate.")
        await interaction.response.send_message(f"✅ {quantidade}x **{nome}** adicionado ao combate.", ephemeral=True)

    @app_commands.command(name="combate_entrar", description="Entra no combate atual")
    async def combate_entrar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return await interaction.response.send_message("❌ Erro.", ephemeral=True)
        if any(p['user_id'] == interaction.user.id for p in session['jogadores']): return await interaction.response.send_message("Já está dentro!", ephemeral=True)

        async with self.bot.db.execute("SELECT id, hp_max, ataque FROM personagens WHERE user_id = ?", (interaction.user.id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados: return await interaction.response.send_message("❌ Sem ficha!", ephemeral=True)
        char_id, hp_max, atk = dados

        # Pre-fetch skills to avoid DB calls in combat loop
        async with self.bot.db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (char_id,)) as cursor:
            skills = await cursor.fetchall()

        session['jogadores'].append({
            'user_id': interaction.user.id, 'personagem_id': char_id,
            'nome': interaction.user.display_name, 'hp': hp_max, 'hp_max': hp_max, 'atk': atk,
            'skills': skills
        })
        await interaction.response.send_message(f"⚔️ **{interaction.user.display_name}** entrou! (HP: {hp_max})", ephemeral=False)

    @app_commands.command(name="combate_iniciar", description="Rola inciativa e começa")
    async def combate_iniciar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return
        if not session["monstros"]:
            return await interaction.response.send_message("❌ Adicione pelo menos um monstro para iniciar.", ephemeral=True)
        
        session['status'] = 'RODANDO'
        
        # Rola Iniciativa
        ordem, log_iniciativa = self._gerar_ordem_iniciativa(session)
        session['ordem'] = ordem
        
        session['log'].append("--- 🎲 INICIATIVAS ---")
        session['log'].extend(log_iniciativa)
        
        # Trava inicial
        session['bloqueado'] = True 
        
        await interaction.response.send_message("🎲 Iniciativas definidas! O combate vai começar...", ephemeral=True)
        
        # Gera a primeira interface e SALVA o ID
        await self.atualizar_interface(interaction.channel, nova_mensagem=True)
        await self._enviar_battlemap(interaction.channel, session)
        await self._emitir_evento_vtt(
            "initiative_order",
            {"ordem": [{"nome": o.get("nome"), "tipo": o["tipo"], "roll": o["roll"]} for o in ordem]},
        )

    @app_commands.command(name="combate_status_jogador", description="🔒 (Mestre) Aplica um status em um jogador.")
    @app_commands.describe(
        alvo="Jogador alvo",
        status="Status (ex: Sangrando)",
    )
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def combate_status_jogador(
        self, interaction: discord.Interaction, alvo: discord.Member, status: str
    ):
        session = self.sessions.get(interaction.channel_id)
        if not session:
            return await interaction.response.send_message(
                "❌ Nenhum combate em andamento.", ephemeral=True
            )
        efeito = STATUS_EFFECTS.get(status)
        if not efeito:
            return await interaction.response.send_message(
                f"❌ Status inválido. Disponíveis: {', '.join(STATUS_EFFECTS.keys())}",
                ephemeral=True,
            )
        key = f"jogador:{alvo.id}"
        session["status_effects"].setdefault(key, []).append(
            {"nome": status, **efeito}
        )
        await interaction.response.send_message(
            f"✅ {status} aplicado em {alvo.display_name}.", ephemeral=True
        )

    @app_commands.command(name="combate_status_monstro", description="🔒 (Mestre) Aplica um status em um monstro.")
    @app_commands.describe(
        monstro_id="ID do monstro no combate",
        status="Status (ex: Sangrando)",
    )
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def combate_status_monstro(
        self, interaction: discord.Interaction, monstro_id: int, status: str
    ):
        session = self.sessions.get(interaction.channel_id)
        if not session:
            return await interaction.response.send_message(
                "❌ Nenhum combate em andamento.", ephemeral=True
            )
        monstro = self._obter_monstro(session, monstro_id)
        if not monstro:
            return await interaction.response.send_message(
                "❌ Monstro não encontrado.", ephemeral=True
            )
        efeito = STATUS_EFFECTS.get(status)
        if not efeito:
            return await interaction.response.send_message(
                f"❌ Status inválido. Disponíveis: {', '.join(STATUS_EFFECTS.keys())}",
                ephemeral=True,
            )
        key = f"monstro:{monstro_id}"
        session["status_effects"].setdefault(key, []).append(
            {"nome": status, **efeito}
        )
        await interaction.response.send_message(
            f"✅ {status} aplicado em {monstro['nome']}.", ephemeral=True
        )

    @app_commands.command(name="combate_mover", description="🔒 (Mestre) Move um token no VTT.")
    @app_commands.describe(token_id="ID do token", x="Nova posição X", y="Nova posição Y")
    @app_commands.check(lambda i: i.user.guild_permissions.administrator)
    async def combate_mover(
        self, interaction: discord.Interaction, token_id: str, x: int, y: int
    ):
        await self._emitir_evento_vtt(
            "token_move", {"token_id": token_id, "position": [x, y]}
        )
        await interaction.response.send_message(
            f"📡 Movimento enviado: Token {token_id} → ({x}, {y}).", ephemeral=True
        )

    @app_commands.command(name="combate_exportar", description="📄 Exporta o log de combate em Markdown.")
    async def combate_exportar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session:
            return await interaction.response.send_message(
                "❌ Nenhum combate em andamento neste canal.", ephemeral=True
            )

        log = session.get("log", [])
        if not log:
            return await interaction.response.send_message(
                "📭 Nenhum log registrado ainda.", ephemeral=True
            )

        conteúdo = "# Log de Combate\n\n" + "\n".join(f"- {linha}" for linha in log)
        buffer = io.StringIO(conteúdo)
        arquivo = discord.File(buffer, filename="log_combate.md")
        await interaction.response.send_message(
            "✅ Log exportado em Markdown.", file=arquivo, ephemeral=True
        )

    async def destravar_turno(self, interaction, channel_id):
        session = self.sessions.get(channel_id)
        if not session: return

        session['bloqueado'] = False
        atual = session['ordem'][session['turno_index']]
        
        # Defer e deleta o botão do mestre para limpar o chat
        await interaction.response.defer()
        try: await interaction.message.delete()
        except: pass
        
        await self._aplicar_status_inicio_turno(session, atual)
        if atual["tipo"] == "MONSTRO":
            monstro = self._obter_monstro(session, atual.get("monstro_id"))
            if monstro and monstro["hp_atual"] <= 0:
                await self.avancar_indice_turno(session)
                session["bloqueado"] = True
                await self.atualizar_interface(interaction.channel)
                return
        else:
            jogador = next(
                (p for p in session["jogadores"] if p["user_id"] == atual["user_id"]), None
            )
            if jogador and jogador["hp"] <= 0:
                await self.avancar_indice_turno(session)
                session["bloqueado"] = True
                await self.atualizar_interface(interaction.channel)
                return

        if atual['tipo'] == 'MONSTRO':
            await self.atualizar_interface(interaction.channel)
            await self.turno_ia_monstro(interaction.channel)
        else:
            await self.atualizar_interface(interaction.channel)

    async def atualizar_interface(self, channel, nova_mensagem=False):
        session = self.sessions.get(channel.id)
        if not session: return

        atual = session['ordem'][session['turno_index']]
        session['turno_monstro'] = (atual['tipo'] == 'MONSTRO')

        desc = f"**📍 Região:** {session.get('regiao', 'Desconhecida')}\n\n"
        desc += self._formatar_monstros(session, atual) + "\n"
        for p in session['jogadores']:
            status = "💀 CAÍDO" if p['hp'] <= 0 else f"{p['hp']}/{p['hp_max']}"
            icone = "👉" if (atual['tipo'] == 'JOGADOR' and atual['user_id'] == p['user_id']) else "👤"
            desc += f"{icone} **{p['nome']}**: {status}\n"

        desc += "\n**📜 Log:**\n" + "\n".join(session['log'][-3:])
        embed = discord.Embed(title="⚔️ Campo de Batalha", description=desc, color=0x2b2d31)
        monstro_thumb = self._monstros_vivos(session)
        if monstro_thumb:
            img = monstro_thumb[0]['img']
            if img:
                embed.set_thumbnail(url=img)

        view = None
        if session['bloqueado']:
            embed.set_footer(text="⏸️ Cena Pausada - Aguardando Narração do Mestre")
            embed.color = 0xFFD700
            # A view do Mestre sempre é uma NOVA mensagem para garantir que ele veja no final do chat
            await channel.send(embed=embed, view=MestreView(self, channel.id))
            return

        if session['turno_monstro']:
            embed.set_footer(text=f"TURNO DO INIMIGO")
            view = CombateView(self, channel.id)
        else:
            skills_do_turno = []
            if atual['tipo'] == 'JOGADOR':
                # Use pre-fetched skills from session
                skills_do_turno = atual.get('skills', [])

            embed.set_footer(text=f"VEZ DE: {atual.get('nome', 'Alguém')}")
            view = CombateView(self, channel.id, habilidades_jogador=skills_do_turno)
            
        # Lógica de Edição vs Nova Mensagem
        if nova_mensagem:
            msg = await channel.send(embed=embed, view=view)
            session['mensagem_id'] = msg.id
        else:
            try:
                msg = await channel.fetch_message(session['mensagem_id'])
                await msg.edit(embed=embed, view=view)
            except:
                # Se falhar (ex: msg deletada), cria uma nova
                msg = await channel.send(embed=embed, view=view)
                session['mensagem_id'] = msg.id

    async def processar_acao_jogador(self, interaction, channel_id, acao, detalhes_skill=None):
        session = self.sessions.get(channel_id)
        jogador = next(p for p in session['jogadores'] if p['user_id'] == interaction.user.id)
        monstro = next((m for m in session['monstros'] if m['hp_atual'] > 0), None)
        if not monstro:
            await interaction.response.send_message("❌ Não há monstros vivos no combate.", ephemeral=True)
            return

        dano = 0
        narrativa = ""
        if acao == "Ataque Básico":
            roll_d20 = random.randint(1, 20)
            dano_total = max(1, (roll_d20 + jogador['atk']) // 2)
            narrativa = f"⚔️ {jogador['nome']} atacou {monstro['nome']}! (🎲{roll_d20} + {jogador['atk']}) -> **{dano_total} dano**"
            dano = dano_total
        elif acao == "Defesa":
            narrativa = f"🛡️ {jogador['nome']} preparou defesa!"
        elif acao == "Habilidade" and detalhes_skill:
            detalhes_rolagem, total = rolar_dados(detalhes_skill['formula'])
            dano = total if detalhes_skill['formula'] else 0
            narrativa = f"✨ {jogador['nome']} usou **{detalhes_skill['nome']}** em {monstro['nome']}! ({detalhes_rolagem or 'Efeito'}) -> **{dano} dano**"

        monstro['hp_atual'] -= dano
        session['log'].append(narrativa)
        if dano > 0:
            ai = self.bot.get_cog("AIHandler")
            if ai:
                arma = detalhes_skill['nome'] if detalhes_skill else "Ataque básico"
                try:
                    resposta = await asyncio.wait_for(
                        ai.gerar_narrativa_combate(jogador['nome'], monstro['nome'], arma, dano),
                        timeout=4,
                    )
                    if resposta:
                        session['log'].append(f"🎭 {resposta}")
                except asyncio.TimeoutError:
                    pass

        await interaction.response.defer()
        
        # --- FIM DE COMBATE COM XP ---
        if monstro['hp_atual'] <= 0:
            session['log'].append(f"💥 {monstro['nome']} foi derrotado!")

        if not self._monstros_vivos(session):
            xp_total = int(sum(m['hp_max'] for m in session['monstros']) * 1.5)
            if xp_total < 10: xp_total = 10

            vivos = [p for p in session['jogadores'] if p['hp'] > 0]
            msg_vitoria = "🏆 **VITÓRIA!** Todos os inimigos foram derrotados!"

            if vivos:
                xp_individual = xp_total // len(vivos)
                msg_vitoria += f"\n🌟 O grupo recebeu **{xp_total} XP** ({xp_individual} p/ cada)."
                for p in vivos:
                    await aplicar_xp(self.bot.db, p['user_id'], xp_individual, interaction.channel)
            else:
                msg_vitoria += "\n💀 Mas todos morreram..."

            await interaction.channel.send(msg_vitoria)
            await self._atualizar_economia_regional(session)
            del self.sessions[channel_id]
            return

        await self.avancar_indice_turno(session)
        session['bloqueado'] = True
        await self.atualizar_interface(interaction.channel)

    async def turno_ia_monstro(self, channel):
        await asyncio.sleep(2)
        session = self.sessions.get(channel.id)
        atual = session['ordem'][session['turno_index']]
        monstro = self._obter_monstro(session, atual.get("monstro_id"))
        if not monstro or monstro["hp_atual"] <= 0:
            await self.avancar_indice_turno(session)
            session['bloqueado'] = True
            await self.atualizar_interface(channel)
            return
        
        alvos = [p for p in session['jogadores'] if p['hp'] > 0]
        if not alvos: return await channel.send("💀 Fim de jogo.")
        alvo = random.choice(alvos)
        
        detalhes, dano = rolar_dados(monstro['dano_base'])
        if dano == 0: dano = 5 

        alvo['hp'] -= dano
        session['log'].append(f"🔥 {monstro['nome']} atacou {alvo['nome']}! ({detalhes}) -> **{dano} dano**")
        ai = self.bot.get_cog("AIHandler")
        if ai and dano > 0:
            try:
                resposta = await asyncio.wait_for(
                    ai.gerar_narrativa_combate(monstro['nome'], alvo['nome'], monstro['dano_base'], dano),
                    timeout=4,
                )
                if resposta:
                    session['log'].append(f"🎭 {resposta}")
            except asyncio.TimeoutError:
                pass
        
        for p in session['ordem']:
            if p.get('user_id') == alvo['user_id']: p['hp'] = alvo['hp']

        await self.avancar_indice_turno(session)
        session['bloqueado'] = True
        await self.atualizar_interface(channel)

    async def avancar_indice_turno(self, session):
        total = len(session['ordem'])
        for _ in range(total):
            session['turno_index'] = (session['turno_index'] + 1) % total
            if session['turno_index'] == 0:
                session['round'] += 1
                ordem, log_iniciativa = self._gerar_ordem_iniciativa(session)
                session['ordem'] = ordem
                total = len(session['ordem'])
                session['log'].append(f"--- 🔄 NOVA RODADA {session['round']} ---")
                session['log'].extend(log_iniciativa)
                await self._emitir_evento_vtt(
                    "initiative_order",
                    {
                        "ordem": [
                            {"nome": o.get("nome"), "tipo": o["tipo"], "roll": o["roll"]}
                            for o in ordem
                        ]
                    },
                )
            atual = session['ordem'][session['turno_index']]

            if atual['tipo'] == 'MONSTRO':
                monstro = self._obter_monstro(session, atual.get("monstro_id"))
                if monstro and monstro['hp_atual'] > 0:
                    return

            jogador_real = next(
                (p for p in session['jogadores'] if p['user_id'] == atual['user_id']), None
            )
            if jogador_real and jogador_real['hp'] > 0:
                return

    async def _atualizar_economia_regional(self, session):
        regiao = session.get("regiao")
        if not regiao:
            return
        async with self.bot.db.execute(
            "SELECT id FROM world_locations WHERE nome LIKE ? LIMIT 1",
            (f"%{regiao}%",),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return
        localizacao_id = row[0]
        ajustes = {
            "Ingredientes de Monstro": -0.05,
            "Comida": 0.05,
        }
        for categoria, delta in ajustes.items():
            async with self.bot.db.execute(
                """
                SELECT modificador
                FROM economia_regional
                WHERE localizacao_id = ? AND categoria = ?
                """,
                (localizacao_id, categoria),
            ) as cursor:
                atual = await cursor.fetchone()
            valor_atual = atual[0] if atual else 1.0
            novo = min(1.3, max(0.7, valor_atual + delta))
            await self.bot.db.execute(
                """
                INSERT INTO economia_regional (localizacao_id, categoria, modificador)
                VALUES (?, ?, ?)
                ON CONFLICT(localizacao_id, categoria)
                DO UPDATE SET modificador = excluded.modificador, atualizado_em = datetime('now')
                """,
                (localizacao_id, categoria, novo),
            )
        await self.bot.db.commit()

async def setup(bot):
    await bot.add_cog(Combat(bot))
