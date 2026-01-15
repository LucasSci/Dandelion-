import discord
import aiosqlite
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from ui.combat_view import CombateView, MestreView, gerar_barra
from utils import rolar_dados

DB_NAME = "bestiario.db"

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    # ... (Mantenha combate_criar e combate_entrar IGUAIS ao anterior) ...
    # Vou repetir apenas as partes que mudaram a lógica
    
    @app_commands.command(name="combate_criar", description="Cria uma sala de batalha")
    async def combate_criar(self, interaction: discord.Interaction, monstro_nome: str):
        # (Código igual ao anterior para buscar monstro)
        async with self.bot.db.execute("SELECT nome, hp_max, imagem_url, iniciativa, dano_base FROM criaturas WHERE nome LIKE ?", (f'%{monstro_nome}%',)) as cursor:
            monster_data = await cursor.fetchone()
        
        if not monster_data: return await interaction.response.send_message("❌ Monstro não encontrado.", ephemeral=True)
        nome, hp, img, ini, dano_base = monster_data
        
        self.sessions[interaction.channel_id] = {
            'status': 'LOBBY',
            'bloqueado': False, # NOVO FLAG
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
        # (Código igual: busca dados do banco e adiciona na session)
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return await interaction.response.send_message("❌ Erro.", ephemeral=True)
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

    # --- MUDANÇA: INICIATIVA E TRAVA INICIAL ---
    @app_commands.command(name="combate_iniciar", description="Rola inciativa e começa")
    async def combate_iniciar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY': return
        
        session['status'] = 'RODANDO'
        
        # 1. Rola Iniciativa (Automático para agilizar, mas exibido no log)
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
        
        # Adiciona resultado ao log
        session['log'].append("--- 🎲 INICIATIVAS ---")
        session['log'].extend(log_iniciativa)
        
        # 2. TRAVA O COMBATE PARA O MESTRE NARRAR O INÍCIO
        session['bloqueado'] = True 
        
        await interaction.response.send_message("🎲 Iniciativas definidas! O combate vai começar...", ephemeral=True)
        await self.atualizar_interface(interaction.channel)

    # --- NOVO: FUNÇÃO DE DESTRAVAR ---
    async def destravar_turno(self, interaction, channel_id):
        session = self.sessions.get(channel_id)
        if not session: return

        # Destrava
        session['bloqueado'] = False
        
        # Verifica de quem é a vez atual
        atual = session['ordem'][session['turno_index']]
        
        # Se for a vez do Monstro, roda a IA imediatamente
        if atual['tipo'] == 'MONSTRO':
            await interaction.response.defer()
            await interaction.message.delete() # Remove botão do mestre
            await self.atualizar_interface(interaction.channel) # Mostra "Turno do Monstro"
            await self.turno_ia_monstro(interaction.channel)
        else:
            # Se for Jogador, apenas atualiza a interface liberando os botões
            await interaction.response.defer()
            await interaction.message.delete()
            await self.atualizar_interface(interaction.channel)

    # --- ATUALIZAÇÃO DA INTERFACE ---
    async def atualizar_interface(self, channel):
        session = self.sessions.get(channel.id)
        if not session: return

        monstro = session['monstro']
        atual = session['ordem'][session['turno_index']]
        session['turno_monstro'] = (atual['tipo'] == 'MONSTRO')

        # Descrição do Embed
        desc = f"**{monstro['nome']}**\n{gerar_barra(monstro['hp_atual'], monstro['hp_max'])} `{monstro['hp_atual']}/{monstro['hp_max']}`\n\n"
        for p in session['jogadores']:
            status = "💀 CAÍDO" if p['hp'] <= 0 else f"{p['hp']}/{p['hp_max']}"
            icone = "👉" if (atual['tipo'] == 'JOGADOR' and atual['user_id'] == p['user_id']) else "👤"
            desc += f"{icone} **{p['nome']}**: {status}\n"

        desc += "\n**📜 Log:**\n" + "\n".join(session['log'][-3:])
        embed = discord.Embed(title="⚔️ Campo de Batalha", description=desc, color=0x2b2d31)
        if monstro['img']: embed.set_thumbnail(url=monstro['img'])

        # --- LÓGICA DA TRAVA ---
        if session['bloqueado']:
            embed.set_footer(text="⏸️ Cena Pausada - Aguardando Narração do Mestre")
            embed.color = 0xFFD700 # Dourado para indicar espera
            # Manda a View do Mestre
            await channel.send(embed=embed, view=MestreView(self, channel.id))
            return

        # Se não estiver bloqueado, segue fluxo normal
        if session['turno_monstro']:
            embed.set_footer(text=f"TURNO DO INIMIGO")
            await channel.send(embed=embed, view=CombateView(self, channel.id))
            # Obs: A IA do monstro é chamada no 'destravar_turno' ou no final do turno do jogador
        else:
            skills_do_turno = []
            if atual['tipo'] == 'JOGADOR':
                 async with self.bot.db.execute("SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?", (atual['personagem_id'],)) as cursor:
                    skills_do_turno = await cursor.fetchall()

            embed.set_footer(text=f"VEZ DE: {atual.get('nome', 'Alguém')}")
            view = CombateView(self, channel.id, habilidades_jogador=skills_do_turno)
            content = f"<@{atual['user_id']}>" if 'user_id' in atual else ""
            await channel.send(content=content, embed=embed, view=view)

    # --- PROCESSAR AÇÃO ---
    async def processar_acao_jogador(self, interaction, channel_id, acao, detalhes_skill=None):
        session = self.sessions.get(channel_id)
        monstro = session['monstro']
        jogador = next(p for p in session['jogadores'] if p['user_id'] == interaction.user.id)

        # (Cálculo de dano - Igual ao anterior)
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
            dano = total if detalhes_skill['formula'] else 0
            narrativa = f"✨ {jogador['nome']} usou **{detalhes_skill['nome']}**! ({detalhes_rolagem or 'Efeito'}) -> **{dano} dano**"

        monstro['hp_atual'] -= dano
        session['log'].append(narrativa)

        # Deleta msg antiga
        await interaction.response.defer()
        try: await interaction.message.delete()
        except: pass

        if monstro['hp_atual'] <= 0:
            return await interaction.channel.send(f"🏆 **VITÓRIA!** O {monstro['nome']} foi derrotado!")

        # --- AQUI ESTÁ O TRUQUE ---
        # Avança o índice do turno, mas TRAVA o sistema
        self.avancar_indice_turno(session)
        session['bloqueado'] = True # <--- Trava para roleplay pós-ação
        
        await self.atualizar_interface(interaction.channel)

    async def turno_ia_monstro(self, channel):
        await asyncio.sleep(2)
        session = self.sessions.get(channel.id)
        monstro = session['monstro']
        
        alvos = [p for p in session['jogadores'] if p['hp'] > 0]
        if not alvos: return await channel.send("💀 Fim de jogo.")
        alvo = random.choice(alvos)
        
        detalhes, dano = rolar_dados(monstro['dano_base'])
        if dano == 0: dano = 5 

        alvo['hp'] -= dano
        session['log'].append(f"🔥 {monstro['nome']} atacou {alvo['nome']}! ({detalhes}) -> **{dano} dano**")
        
        for p in session['ordem']:
            if p.get('user_id') == alvo['user_id']: p['hp'] = alvo['hp']

        # Fim do turno do monstro: Avança índice e TRAVA
        self.avancar_indice_turno(session)
        session['bloqueado'] = True
        
        await self.atualizar_interface(channel)

    def avancar_indice_turno(self, session):
        # Apenas move o ponteiro para o próximo vivo
        start_index = session['turno_index']
        for _ in range(len(session['ordem'])):
            session['turno_index'] = (session['turno_index'] + 1) % len(session['ordem'])
            atual = session['ordem'][session['turno_index']]
            
            if atual['tipo'] == 'MONSTRO': return
            
            # Checa se jogador está vivo
            jogador_real = next((p for p in session['jogadores'] if p['user_id'] == atual['user_id']), None)
            if jogador_real and jogador_real['hp'] > 0: return

async def setup(bot):
    await bot.add_cog(Combat(bot))