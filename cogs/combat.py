import discord
import aiosqlite
import random
import asyncio
import logging
from discord.ext import commands
from discord import app_commands
from ui.combat_view import CombateView, MestreView, gerar_barra
from utils import rolar_dados

log = logging.getLogger(__name__)

# --- HELPER: SISTEMA DE XP ---
async def aplicar_xp(db, user_id, xp_ganho, channel):
    """Calcula XP, verifica Level Up e atualiza o banco."""
    async with db.execute("SELECT nivel, xp_atual, hp_max, ataque FROM personagens WHERE user_id = ?", (user_id,)) as cursor:
        dados = await cursor.fetchone()
    
    if not dados: return
    nivel, xp, hp, atk = dados
    
    xp_prox_nivel = nivel * 1000 
    novo_xp = xp + xp_ganho
    msg = ""

    if novo_xp >= xp_prox_nivel:
        novo_nivel = nivel + 1
        novo_xp = novo_xp - xp_prox_nivel
        novo_hp = hp + 5   
        novo_atk = atk + 1 
        
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

    def obter_resumo_combate(self, channel_id):
        session = self.sessions.get(channel_id)
        if not session: return "Nenhum combate ocorrendo."
        monstro = session['monstro']
        jogadores_str = ", ".join([f"{p['nome']} (HP:{p['hp']})" for p in session['jogadores']])
        return f"Inimigo: {monstro['nome']} ({monstro['hp_atual']}/{monstro['hp_max']}). Heróis: {jogadores_str}."

    @app_commands.command(name="combate_criar", description="Cria uma sala de batalha")
    async def combate_criar(self, interaction: discord.Interaction, monstro_nome: str):
        async with self.bot.db.execute("SELECT nome, hp_max, imagem_url, iniciativa, dano_base FROM criaturas WHERE nome LIKE ?", (f'%{monstro_nome}%',)) as cursor:
            monster_data = await cursor.fetchone()
        
        if not monster_data: return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)
        nome, hp, img, ini, dano_base = monster_data
        
        self.sessions[interaction.channel_id] = {
            'status': 'LOBBY',
            'bloqueado': False,
            'mensagem_id': None, 
            'monstro': {'nome': nome, 'hp_max': hp, 'hp_atual': hp, 'img': img, 'ini': ini, 'dano_base': dano_base},
            'jogadores': [],
            'ordem': [],
            'turno_index': 0,
            'turno_monstro': False,
            'log': [f"Um {nome} selvagem apareceu!"]
        }
        embed = discord.Embed(title=f"⚠️ COMBATE: {nome}", description=f"HP: {hp}\n\n**Aguardando guerreiros...**", color=0xFF0000)
        if img: embed.set_image(url=img)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="combate_entrar", description="Entra no combate atual")
    async def combate_entrar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return await interaction.response.send_message("❌ Nenhuma batalha em preparação.", ephemeral=True)
        if any(p['user_id'] == interaction.user.id for p in session['jogadores']): return await interaction.response.send_message("Já está dentro!", ephemeral=True)

        async with self.bot.db.execute("SELECT id, hp_max, ataque FROM personagens WHERE user_id = ?", (interaction.user.id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados: return await interaction.response.send_message("❌ Sem ficha!", ephemeral=True)
        char_id, hp_max, atk = dados

        session['jogadores'].append({
            'user_id': interaction.user.id, 'personagem_id': char_id,
            'nome': interaction.user.display_name, 'hp': hp_max, 'hp_max': hp_max, 'atk': atk
        })
        await interaction.response.send_message(f"⚔️ **{interaction.user.display_name}** entrou! (HP: {hp_max})", ephemeral=False)

    @app_commands.command(name="combate_iniciar", description="Rola inciativa e começa")
    async def combate_iniciar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return
        
        session['status'] = 'RODANDO'
        
        # Iniciativa
        ordem = []
        log_iniciativa = []
        for p in session['jogadores']:
            roll = random.randint(1, 20)
            ordem.append({**p, 'tipo': 'JOGADOR', 'roll': roll})
            log_iniciativa.append(f"{p['nome']}: 🎲 {roll}")
        
        monstro = session['monstro']
        roll_monstro = random.randint(1, 20) + (monstro['ini'] or 0)
        ordem.append({'tipo': 'MONSTRO', 'nome': monstro['nome'], 'roll': roll_monstro})
        log_iniciativa.append(f"{monstro['nome']}: 🎲 {roll_monstro}")
        
        ordem.sort(key=lambda x: x['roll'], reverse=True)
        session['ordem'] = ordem
        
        session['log'].append("--- 🎲 INICIATIVAS ---")
        session['log'].extend(log_iniciativa)
        session['bloqueado'] = True 
        
        await interaction.response.send_message("🎲 Iniciativas definidas! Preparando o campo...", ephemeral=True)
        
        # Envia a PRIMEIRA mensagem do painel e salva o ID
        await self.atualizar_interface(interaction.channel, force_new=True)

    async def destravar_turno(self, interaction, channel_id):
        session = self.sessions.get(channel_id)
        if not session: return

        session['bloqueado'] = False
        atual = session['ordem'][session['turno_index']]
        
        # Deleta a mensagem do mestre para limpar o chat
        await interaction.response.defer()
        try: await interaction.message.delete()
        except: pass
        
        await self.atualizar_interface(interaction.channel)
        
        if atual['tipo'] == 'MONSTRO':
            await self.turno_ia_monstro(interaction.channel)

    async def atualizar_interface(self, channel, force_new=False):
        """Atualiza a mensagem principal do combate. Usa EDIT preferencialmente."""
        session = self.sessions.get(channel.id)
        if not session: return

        monstro = session['monstro']
        atual = session['ordem'][session['turno_index']]
        session['turno_monstro'] = (atual['tipo'] == 'MONSTRO')

        desc = f"**{monstro['nome']}**\n{gerar_barra(monstro['hp_atual'], monstro['hp_max'])} `{monstro['hp_atual']}/{monstro['hp_max']}`\n\n"
        for p in session['jogadores']:
            status = "💀 CAÍDO" if p['hp'] <= 0 else f"{p['hp']}/{p['hp_max']}"
            icone = "👉" if (atual['tipo'] == 'JOGADOR' and atual['user_id'] == p['user_id']) else "👤"
            desc += f"{icone} **{p['nome']}**: {status}\n"

        desc += "\n**📜 Log:**\n" + "\n".join(session['log'][-3:])
        embed = discord.Embed(title="⚔️ Campo de Batalha", description=desc, color=0x2b2d31)
        if monstro['img']: embed.set_thumbnail(url=monstro['img'])

        view = None
        if session['bloqueado']:
            embed.set_footer(text="⏸️ Cena Pausada - Aguardando Narração do Mestre")
            embed.color = 0xFFD700
            # Mestre View é sempre nova para aparecer no fundo
            return await channel.send(embed=embed, view=MestreView(self, channel.id))

        if session['turno_monstro']:
            embed.set_footer(text=f"TURNO DO INIMIGO")
            view = CombateView(self, channel.id)
        else:
            skills_do_turno = []
            if atual['tipo'] == 'JOGADOR':
                 async with self.bot.db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (atual['personagem_id'],)) as cursor:
                    skills_do_turno = await cursor.fetchall()
            embed.set_footer(text=f"VEZ DE: {atual.get('nome', 'Alguém')}")
            view = CombateView(self, channel.id, habilidades_jogador=skills_do_turno)
            
        if force_new:
            msg = await channel.send(embed=embed, view=view)
            session['mensagem_id'] = msg.id
        elif session.get('mensagem_id'):
            try:
                msg = await channel.fetch_message(session['mensagem_id'])
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                # Se deletaram a mensagem, cria outra
                msg = await channel.send(embed=embed, view=view)
                session['mensagem_id'] = msg.id
        else:
            msg = await channel.send(embed=embed, view=view)
            session['mensagem_id'] = msg.id

    async def processar_acao_jogador(self, interaction, channel_id, acao, detalhes_skill=None):
        session = self.sessions.get(channel_id)
        monstro = session['monstro']
        jogador = next(p for p in session['jogadores'] if p['user_id'] == interaction.user.id)

        dano = 0
        narrativa = ""
        if acao == "Ataque Básico":
            roll_d20 = random.randint(1, 20)
            dano_total = max(1, (roll_d20 + jogador['atk']) // 2)
            narrativa = f"⚔️ {jogador['nome']} atacou! (🎲{roll_d20} + {jogador['atk']}) -> **{dano_total} dano**"
            dano = dano_total
        elif acao == "Defesa":
            narrativa = f"🛡️ {jogador['nome']} preparou defesa!"
        elif acao == "Habilidade" and detalhes_skill:
            detalhes_rolagem, total = rolar_dados(detalhes_skill['formula'])
            dano = total if total else 0
            narrativa = f"✨ {jogador['nome']} usou **{detalhes_skill['nome']}**! -> **{dano} dano**"

        monstro['hp_atual'] -= dano
        session['log'].append(narrativa)

        await interaction.response.defer()
        
        # Check Fim de Combate
        if monstro['hp_atual'] <= 0:
            xp_total = int(monstro['hp_max'] * 1.5)
            xp_total = max(10, xp_total)

            vivos = [p for p in session['jogadores'] if p['hp'] > 0]
            msg_vitoria = f"🏆 **VITÓRIA!** O {monstro['nome']} foi derrotado!"
            
            if vivos:
                xp_individual = xp_total // len(vivos)
                msg_vitoria += f"\n🌟 O grupo recebeu **{xp_total} XP** ({xp_individual} p/ cada)."
                for p in vivos:
                    await aplicar_xp(self.bot.db, p['user_id'], xp_individual, interaction.channel)
            else:
                msg_vitoria += "\n💀 Mas todos morreram..."

            await interaction.channel.send(msg_vitoria)
            del self.sessions[channel_id]
            return

        self.avancar_indice_turno(session)
        session['bloqueado'] = True
        await self.atualizar_interface(interaction.channel)

    async def turno_ia_monstro(self, channel):
        await asyncio.sleep(2)
        session = self.sessions.get(channel.id)
        if not session: return # Combate pode ter acabado nesse tempo
        
        monstro = session['monstro']
        
        alvos = [p for p in session['jogadores'] if p['hp'] > 0]
        if not alvos: return await channel.send("💀 Fim de jogo.")
        alvo = random.choice(alvos)
        
        detalhes, dano = rolar_dados(monstro['dano_base'])
        if dano == 0: dano = 5 

        alvo['hp'] -= dano
        session['log'].append(f"🔥 {monstro['nome']} atacou {alvo['nome']}! ({detalhes}) -> **{dano} dano**")
        
        # Sincroniza HP na ordem
        for p in session['ordem']:
            if p.get('user_id') == alvo['user_id']: p['hp'] = alvo['hp']

        self.avancar_indice_turno(session)
        session['bloqueado'] = True
        await self.atualizar_interface(channel)

    def avancar_indice_turno(self, session):
        for _ in range(len(session['ordem'])):
            session['turno_index'] = (session['turno_index'] + 1) % len(session['ordem'])
            atual = session['ordem'][session['turno_index']]
            
            if atual['tipo'] == 'MONSTRO': return
            
            jogador_real = next((p for p in session['jogadores'] if p['user_id'] == atual['user_id']), None)
            if jogador_real and jogador_real['hp'] > 0: return

async def setup(bot):
    await bot.add_cog(Combat(bot))