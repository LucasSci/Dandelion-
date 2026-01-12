import discord
import aiosqlite
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from ui.combat_view import CombateView, gerar_barra

DB_NAME = "bestiario.db"

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Armazena as sessões ativas na memória: {channel_id: dados_sessao}
        self.sessions = {}

    # ==========================
    # GERENCIAMENTO DE LOBBY
    # ==========================

    @app_commands.command(name="combate_criar", description="Cria uma sala de batalha contra um monstro")
    async def combate_criar(self, interaction: discord.Interaction, monstro_nome: str):
        # Busca monstro no DB
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT nome, hp_max, imagem_url, iniciativa, dano_base FROM criaturas WHERE nome LIKE ?", (f'%{monstro_nome}%',)) as cursor:
                monster_data = await cursor.fetchone()
        
        if not monster_data:
            return await interaction.response.send_message("❌ Monstro não encontrado no bestiário.", ephemeral=True)

        nome, hp, img, ini, dano = monster_data
        
        # Cria a sessão
        self.sessions[interaction.channel_id] = {
            'status': 'LOBBY', # LOBBY, INICIANDO, RODANDO
            'monstro': {
                'nome': nome, 
                'hp_max': hp, 
                'hp_atual': hp, 
                'img': img, 
                'ini': ini, 
                'dano': dano
            },
            'jogadores': [], # Lista de dicts {user_id, nome, hp, ini}
            'ordem': [], # Lista ordenada de turnos
            'turno_index': 0,
            'turno_monstro': False,
            'log': ["O monstro ruge! Digite `/combate_entrar` para lutar!"]
        }

        embed = discord.Embed(title=f"⚠️ COMBATE: {nome}", description=f"HP: {hp}\n\n**Jogadores:**\n(Nenhum)", color=0xFF0000)
        if img: embed.set_image(url=img)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="combate_entrar", description="Entra no combate atual do canal")
    async def combate_entrar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY':
            return await interaction.response.send_message("❌ Nenhum lobby aberto neste canal.", ephemeral=True)

        if any(p['user_id'] == interaction.user.id for p in session['jogadores']):
            return await interaction.response.send_message("Você já está na luta!", ephemeral=True)

        # Adiciona jogador (Idealmente buscaria HP da ficha dele no DB)
        session['jogadores'].append({
            'user_id': interaction.user.id,
            'nome': interaction.user.display_name,
            'hp': 30, # HP Padrão por enquanto
            'hp_max': 30
        })

        await interaction.response.send_message(f"⚔️ **{interaction.user.display_name}** sacou a espada!", ephemeral=False)

    @app_commands.command(name="combate_iniciar", description="Começa a pancadaria")
    async def combate_iniciar(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.channel_id)
        if not session or session['status'] != 'LOBBY':
            return await interaction.response.send_message("❌ Erro no lobby.", ephemeral=True)

        if not session['jogadores']:
            return await interaction.response.send_message("❌ Precisa de pelo menos 1 jogador!", ephemeral=True)

        session['status'] = 'RODANDO'
        
        # Rola Iniciativa
        ordem = []
        # 1. Jogadores
        for p in session['jogadores']:
            roll = random.randint(1, 20)
            ordem.append({**p, 'tipo': 'JOGADOR', 'roll': roll})
        
        # 2. Monstro
        monstro = session['monstro']
        roll_monstro = random.randint(1, 20) + (monstro['ini'] or 0)
        ordem.append({'tipo': 'MONSTRO', 'nome': monstro['nome'], 'roll': roll_monstro})

        # Ordena maior para menor
        ordem.sort(key=lambda x: x['roll'], reverse=True)
        session['ordem'] = ordem
        
        await interaction.response.send_message("🎲 Rolando iniciativas...", ephemeral=True)
        await self.atualizar_interface(interaction.channel)

    # ==========================
    # LÓGICA DE TURNOS
    # ==========================

    async def atualizar_interface(self, channel):
        session = self.sessions.get(channel.id)
        if not session: return

        monstro = session['monstro']
        atual = session['ordem'][session['turno_index']]
        session['turno_monstro'] = (atual['tipo'] == 'MONSTRO')

        # Constrói o Embed
        desc = f"**{monstro['nome']}**\n{gerar_barra(monstro['hp_atual'], monstro['hp_max'])} `{monstro['hp_atual']}/{monstro['hp_max']}`\n\n"
        
        # Lista Jogadores
        for p in session['jogadores']:
            status = "💀 CAÍDO" if p['hp'] <= 0 else f"{p['hp']}/{p['hp_max']}"
            icone = "👉" if (atual['tipo'] == 'JOGADOR' and atual['user_id'] == p['user_id']) else "👤"
            desc += f"{icone} **{p['nome']}**: {status}\n"

        desc += "\n**📜 Últimos Eventos:**\n" + "\n".join(session['log'][-3:])

        embed = discord.Embed(title="⚔️ Campo de Batalha", description=desc, color=0x2b2d31)
        if monstro['img']: embed.set_thumbnail(url=monstro['img'])
        
        if session['turno_monstro']:
            embed.set_footer(text=f"TURNO DO MONSTRO! (Automático)")
            # Envia a interface bloqueada e roda a IA do monstro
            view = CombateView(self, channel.id) # Bloqueia botões
            await channel.send(embed=embed, view=view)
            await self.turno_ia_monstro(channel)
        else:
            embed.set_footer(text=f"VEZ DE: {atual['nome']}")
            view = CombateView(self, channel.id)
            await channel.send(content=f"<@{atual['user_id']}>, é sua vez!", embed=embed, view=view)

    async def processar_acao_jogador(self, interaction, channel_id, acao):
        session = self.sessions.get(channel_id)
        monstro = session['monstro']
        jogador = session['ordem'][session['turno_index']]

        # Simula Dano
        dano = 0
        narrativa = ""
        
        if acao == "Ataque Básico":
            dano = random.randint(5, 12)
            narrativa = f"⚔️ {jogador['nome']} acertou um golpe ({dano} de dano)!"
        elif acao == "Defesa":
            narrativa = f"🛡️ {jogador['nome']} entrou em postura defensiva."
        else: # Habilidade
            dano = random.randint(10, 20)
            narrativa = f"✨ {jogador['nome']} usou uma técnica secreta ({dano} de dano)!"

        monstro['hp_atual'] -= dano
        session['log'].append(narrativa)

        await interaction.response.defer()
        await interaction.message.delete() # Limpa msg antiga

        if monstro['hp_atual'] <= 0:
            return await interaction.channel.send(f"🏆 **VITÓRIA!** {monstro['nome']} foi derrotado!")

        self.proximo_turno(channel_id)
        await self.atualizar_interface(interaction.channel)

    async def turno_ia_monstro(self, channel):
        await asyncio.sleep(3) # Suspense
        session = self.sessions.get(channel.id)
        monstro = session['monstro']
        
        # Escolhe alvo aleatório vivo
        alvos = [p for p in session['jogadores'] if p['hp'] > 0]
        if not alvos:
            return await channel.send("💀 O monstro dizimou a equipe...")

        alvo = random.choice(alvos)
        
        # Rola ataque
        dano = random.randint(5, 15) # Exemplo simples
        alvo['hp'] -= dano
        
        session['log'].append(f"🔥 {monstro['nome']} atacou {alvo['nome']} causando {dano} de dano!")
        
        self.proximo_turno(channel.id)
        await self.atualizar_interface(channel)

    def proximo_turno(self, channel_id):
        session = self.sessions.get(channel_id)
        session['turno_index'] = (session['turno_index'] + 1) % len(session['ordem'])
        
        # Pula quem está morto (se for jogador)
        atual = session['ordem'][session['turno_index']]
        if atual['tipo'] == 'JOGADOR':
             # Acha o dict do jogador real para ver HP atualizado
             dados_reais = next(p for p in session['jogadores'] if p['user_id'] == atual['user_id'])
             if dados_reais['hp'] <= 0:
                 self.proximo_turno(channel_id) # Recursivo para pular

async def setup(bot):
    await bot.add_cog(Combat(bot))