import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
from scripts.contract_gen import gerar_imagem_contrato

# ==============================================================================
# VIEW DO FÓRUM (Jogadores aceitam aqui)
# ==============================================================================
class QuestPostView(ui.View):
    def __init__(self, db):
        super().__init__(timeout=None)
        self.db = db

    async def update_embed(self, interaction, q_data, parts):
        q_id, tit, desc, gp, xp, st, cls, reg, max_p, mob, img = q_data
        
        cur_p = len(parts)
        if st == "Concluida": cor, txt = 0x95A5A6, "🏁 Concluída"
        elif cur_p >= max_p:  cor, txt = 0xED4245, "🔴 Grupo Cheio"
        elif cur_p > 0:       cor, txt = 0xFEE75C, f"🟡 {cur_p}/{max_p}"
        else:                 cor, txt = 0x57F287, "🟢 Disponível"

        emb = discord.Embed(title=f"📜 {tit}", description=desc, color=cor)
        if img and img.startswith("http"): emb.set_image(url=img)
        emb.add_field(name="🌍 Região", value=reg, inline=True)
        emb.add_field(name="👹 Alvo", value=mob or "Nenhum", inline=True)
        emb.add_field(name="👥 Vagas", value=f"{cur_p}/{max_p}", inline=True)
        emb.add_field(name="💰 Loot", value=f"{gp}G | {xp}XP", inline=True)
        emb.add_field(name="🛡️ Req", value=cls, inline=True)
        emb.add_field(name="Status", value=txt, inline=False)
        
        if parts:
            names = []
            for uid in parts:
                m = interaction.guild.get_member(uid)
                names.append(f"• {m.display_name}" if m else f"ID {uid}")
            emb.add_field(name="Inscritos", value="\n".join(names), inline=False)
        
        return emb

    @ui.button(label="Aceitar Contrato", style=discord.ButtonStyle.success, emoji="✍️", custom_id="btn_aceitar_v5")
    async def btn_aceitar(self, interaction: discord.Interaction, button: ui.Button):
        thread_id = interaction.channel_id
        
        # Busca Quest
        query = "SELECT id, titulo, descricao, recompensa_ouro, recompensa_xp, status, classes_req, regiao, max_jogadores, alvo_monstro_nome, imagem_url FROM quests WHERE thread_id=?"
        async with self.db.execute(query, (thread_id,)) as c: q = await c.fetchone()
        
        if not q: return await interaction.response.send_message("❌ Quest não encontrada/inválida.", ephemeral=True)
        q_id, _, _, _, _, status, req, _, max_p, _, _ = q

        if status == "Rascunho": return await interaction.response.send_message("🚧 Esta missão ainda é um rascunho.", ephemeral=True)
        if status == "Concluida": return await interaction.response.send_message("🏁 Encerrada.", ephemeral=True)

        # Checa Participantes
        async with self.db.execute("SELECT user_id FROM quest_participantes WHERE quest_id=?", (q_id,)) as c:
            rows = await c.fetchall()
            parts = [r[0] for r in rows]

        if interaction.user.id in parts: return await interaction.response.send_message("⚠️ Já está inscrito.", ephemeral=True)
        if len(parts) >= max_p: return await interaction.response.send_message("🚫 Cheio.", ephemeral=True)

        # Checa Classe
        async with self.db.execute("SELECT classe FROM personagens WHERE user_id=?", (interaction.user.id,)) as c:
            char = await c.fetchone()
        if not char: return await interaction.response.send_message("❌ Crie ficha.", ephemeral=True)
        
        p_cls = char[0].lower()
        allowed = [x.strip().lower() for x in req.split(',')]
        if "todas" not in allowed and p_cls not in allowed:
            return await interaction.response.send_message(f"🚫 Classe {char[0]} não permitida.", ephemeral=True)

        # Insere
        await self.db.execute("INSERT INTO quest_participantes (quest_id, user_id) VALUES (?,?)", (q_id, interaction.user.id))
        
        if status == "Disponivel":
            await self.db.execute("UPDATE quests SET status='Em Andamento' WHERE id=?", (q_id,))
            q = list(q); q[5] = "Em Andamento"; q = tuple(q)
        
        await self.db.commit()
        
        parts.append(interaction.user.id)
        new_emb = await self.update_embed(interaction, q, parts)
        if len(parts) >= max_p:
            button.label = "Grupo Cheio"
            button.style = discord.ButtonStyle.danger
        
        await interaction.response.edit_message(embed=new_emb, view=self)
        await interaction.followup.send(f"✅ {interaction.user.mention} entrou!", ephemeral=False)

# ==============================================================================
# COG PRINCIPAL
# ==============================================================================

class Quests(commands.Cog):
    def __init__(self, bot): self.bot = bot
    def is_mestre(i: discord.Interaction): return i.user.guild_permissions.administrator
    async def cog_load(self): self.bot.add_view(QuestPostView(self.bot.db))

    # --- AUTOCOMPLETES ---
    async def ac_monstro(self, i, c: str):
        async with self.bot.db.execute("SELECT id, name FROM monsters WHERE name LIKE ? LIMIT 25", (f'%{c}%',)) as r:
            return [app_commands.Choice(name=x[1], value=str(x[0])) for x in await r.fetchall()]
    
    async def ac_quest_rascunho(self, i, c: str):
        # Mostra apenas Rascunhos para publicar
        async with self.bot.db.execute("SELECT id, titulo FROM quests WHERE status='Rascunho' AND titulo LIKE ? LIMIT 25", (f'%{c}%',)) as r:
            return [app_commands.Choice(name=f"[Rascunho] {x[1]}", value=str(x[0])) for x in await r.fetchall()]

    async def ac_quest_ativa(self, i, c: str):
        async with self.bot.db.execute("SELECT id, titulo FROM quests WHERE status IN ('Em Andamento','Disponivel') AND titulo LIKE ? LIMIT 25", (f'%{c}%',)) as r:
            return [app_commands.Choice(name=f"{x[1]}", value=str(x[0])) for x in await r.fetchall()]

    async def regiao_autocomplete(self, interaction: discord.Interaction, current: str):
        regioes = ["Zerrikania", "Deserto de Korath", "Novigrad", "Velen", "Skellige", "Kaer Morhen", "Toussaint", "Ofir", "Brokilon"]
        return [app_commands.Choice(name=r, value=r) for r in regioes if current.lower() in r.lower()]

    async def classes_autocomplete(self, interaction: discord.Interaction, current: str):
        opcoes = ["Todas", "Bruxo", "Feiticeira", "Bardo", "Guerreiro", "Ladino", "Bruxo,Feiticeira", "Guerreiro,Arqueiro"]
        return [app_commands.Choice(name=o, value=o) for o in opcoes if current.lower() in o.lower()]

    # --- COMANDOS ---

    @app_commands.command(name="quest_criar", description="🔒 (Mestre) Cria missão manualmente (com opções completas)")
    @app_commands.describe(
        titulo="Título", descricao="Objetivo", regiao="Local", ouro="Recompensa G", xp="Recompensa XP",
        canal_forum="Fórum do Discord", jogadores="Max Players", classes="Classes permitidas",
        monstro_db="Vincular criatura do Bestiário", jogador_alvo="Já adicionar um player?"
    )
    @app_commands.autocomplete(monstro_db=ac_monstro, regiao=regiao_autocomplete, classes=classes_autocomplete)
    @app_commands.check(is_mestre)
    async def quest_criar(self, interaction: discord.Interaction, 
                          titulo: str, descricao: str, regiao: str, 
                          ouro: int, xp: int, canal_forum: discord.ForumChannel,
                          classes: str = "Todas", jogadores: int = 4, 
                          monstro_db: Optional[str] = None, jogador_alvo: Optional[discord.Member] = None):
        
        await interaction.response.defer()

        # Resolver Monstro
        criatura_id = None
        nome_monstro = "Nenhum"
        if monstro_db:
            try:
                criatura_id = int(monstro_db)
                async with self.bot.db.execute("SELECT name FROM monsters WHERE id=?", (criatura_id,)) as c:
                    res = await c.fetchone()
                    if res: nome_monstro = res[0]
            except: pass

        # Gerar Imagem do Contrato
        file_contrato = None
        try:
            buffer = await gerar_imagem_contrato(titulo, descricao, f"{ouro}G")
            if buffer: file_contrato = discord.File(buffer, filename="contrato.png")
        except Exception as e: print(f"Erro imagem contrato: {e}")

        # Embed Inicial
        embed = discord.Embed(title=f"📜 {titulo}", description=descricao, color=0x57F287)
        embed.add_field(name="🌍 Região", value=regiao, inline=True)
        embed.add_field(name="👹 Alvo", value=nome_monstro, inline=True)
        
        qtd_inicial = 1 if jogador_alvo else 0
        embed.add_field(name="👥 Vagas", value=f"{qtd_inicial} / {jogadores}", inline=True)
        embed.add_field(name="💰 Recompensas", value=f"**{ouro}G** | **{xp}XP**", inline=True)
        embed.add_field(name="🛡️ Classes", value=classes, inline=True)
        embed.add_field(name="Estado", value="🟢 Disponível" if not jogador_alvo else "🟡 Formando Grupo", inline=False)
        
        if jogador_alvo:
            embed.add_field(name="🗡️ Aventureiros Inscritos", value=f"• {jogador_alvo.display_name}", inline=False)

        # Postar no Forum
        files = [file_contrato] if file_contrato else []
        try:
            thread_msg = await canal_forum.create_thread(name=f"[Contrato] {titulo}", embed=embed, files=files, view=QuestPostView(self.bot.db))
            thread = thread_msg.thread
        except Exception as e: return await interaction.followup.send(f"❌ Erro thread: {e}")

        # Salvar
        status = 'Em Andamento' if jogador_alvo else 'Disponivel'
        cursor = await self.bot.db.execute("""
            INSERT INTO quests (titulo, descricao, recompensa_ouro, recompensa_xp, status, classes_req, 
                                regiao, max_jogadores, alvo_monstro_nome, criatura_id, thread_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
        """, (titulo, descricao, ouro, xp, status, classes, regiao, jogadores, nome_monstro, criatura_id, thread.id))
        
        q_id = (await cursor.fetchone())[0]

        if jogador_alvo:
            await self.bot.db.execute("INSERT INTO quest_participantes (quest_id, user_id) VALUES (?,?)", (q_id, jogador_alvo.id))
            await thread.send(f"📩 {jogador_alvo.mention}, você foi designado para esta missão!")

        await self.bot.db.commit()
        await interaction.followup.send(f"✅ Criada em {thread.mention}!", ephemeral=True)

    @app_commands.command(name="quest_gerar", description="🔒 (Mestre) IA cria missão cronológica. Padrão: Rascunho.")
    @app_commands.choices(dificuldade=[
        app_commands.Choice(name="Fácil", value="Fácil"),
        app_commands.Choice(name="Média", value="Média"),
        app_commands.Choice(name="Difícil", value="Difícil")
    ])
    @app_commands.check(is_mestre)
    async def gerar(self, i: discord.Interaction, dificuldade: str, publicar_agora: bool = False, canal_forum: Optional[discord.ForumChannel] = None):
        """
        Se publicar_agora = False (padrão), cria um Rascunho visível só aqui.
        Se publicar_agora = True, exige canal_forum e posta direto.
        """
        if publicar_agora and not canal_forum:
            return await i.response.send_message("❌ Para publicar agora, selecione um `canal_forum`.", ephemeral=True)

        await i.response.defer(ephemeral=not publicar_agora) # Se for rascunho, é ephemeral
        ai = self.bot.get_cog("AIHandler")
        if not ai: return await i.followup.send("IA Off.")

        # 1. Gera baseada na Cronologia (Memória) com NOTA
        d = await ai.gerar_quest_cronologica(dificuldade)
        if not d: return await i.followup.send("Erro IA.")

        # 2. Imagens
        img_url = await ai.gerar_imagem_dalle(d['prompt_img'])
        file_contrato = None
        try:
            buf = await gerar_imagem_contrato(d['titulo'], d['descricao'], f"{d['ouro']}G")
            if buf: file_contrato = discord.File(buf, filename="contrato.png")
        except: pass

        # Embed Preview
        embed = discord.Embed(title=f"📜 {d['titulo']}", description=d['descricao'], color=0x95A5A6 if not publicar_agora else 0x57F287)
        if img_url: embed.set_image(url=img_url)
        embed.add_field(name="Info", value=f"📍 {d['regiao']} | 👹 {d['monstro']}")
        embed.add_field(name="Recompensa", value=f"{d['ouro']}G | {d['xp']}XP")
        
        # AQUI MOSTRA A NOTA DA IA NO RASCUNHO
        if not publicar_agora:
            embed.add_field(name="🔐 Nota de Lógica (IA)", value=f"*{d['nota_mestre']}*", inline=False)
            embed.add_field(name="Status", value="📝 RASCUNHO (Privado)")
        else:
            embed.add_field(name="Status", value="🟢 PUBLICADO")

        files = [file_contrato] if file_contrato else []
        
        thread_id = None
        status_db = 'Rascunho'

        if publicar_agora:
            try:
                t_msg = await canal_forum.create_thread(name=f"[Contrato] {d['titulo']}", embed=embed, files=files, view=QuestPostView(self.bot.db))
                thread_id = t_msg.thread.id
                status_db = 'Disponivel'
                await i.followup.send(f"✅ Publicado em {t_msg.thread.mention}")
            except Exception as e:
                return await i.followup.send(f"Erro Discord: {e}")
        else:
            # Modo Rascunho
            await i.followup.send("📝 **Quest Gerada (Rascunho)**\nUse `/quest_publicar` para enviar ao fórum quando quiser.", embed=embed, files=files)

        # Salva
        await self.bot.db.execute("""
            INSERT INTO quests (titulo, descricao, recompensa_ouro, recompensa_xp, status, classes_req, regiao, alvo_monstro_nome, imagem_url, nota_mestre, thread_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (d['titulo'], d['descricao'], d['ouro'], d['xp'], status_db, d['classes'], d['regiao'], d['monstro'], img_url, d['nota_mestre'], thread_id))
        await self.bot.db.commit()

    @app_commands.command(name="quest_publicar", description="🔒 (Mestre) Publica um Rascunho no Fórum")
    @app_commands.autocomplete(rascunho_id=ac_quest_rascunho)
    @app_commands.check(is_mestre)
    async def publicar(self, i: discord.Interaction, rascunho_id: str, canal_forum: discord.ForumChannel):
        try: q_id = int(rascunho_id)
        except: return await i.response.send_message("ID inválido.", ephemeral=True)

        async with self.bot.db.execute("SELECT titulo, descricao, recompensa_ouro, recompensa_xp, classes_req, regiao, alvo_monstro_nome, imagem_url FROM quests WHERE id=?", (q_id,)) as c:
            q = await c.fetchone()
        
        if not q: return await i.response.send_message("Quest não encontrada.", ephemeral=True)
        tit, desc, gp, xp, cls, reg, mob, img = q

        await i.response.defer()

        f_files = []
        try:
            buf = await gerar_imagem_contrato(tit, desc, f"{gp}G")
            if buf: f_files.append(discord.File(buf, filename="contrato.png"))
        except: pass

        emb = discord.Embed(title=f"📜 {tit}", description=desc, color=0x57F287)
        if img: emb.set_image(url=img)
        emb.add_field(name="🌍 Região", value=reg)
        emb.add_field(name="👹 Alvo", value=mob)
        emb.add_field(name="👥 Vagas", value="0 / 4")
        emb.add_field(name="💰 Loot", value=f"{gp}G | {xp}XP")
        emb.add_field(name="Req", value=cls)
        emb.add_field(name="Estado", value="🟢 Disponível", inline=False)

        try:
            t_msg = await canal_forum.create_thread(name=f"[Contrato] {tit}", embed=emb, files=f_files, view=QuestPostView(self.bot.db))
            
            await self.bot.db.execute("UPDATE quests SET status='Disponivel', thread_id=? WHERE id=?", (t_msg.thread.id, q_id))
            await self.bot.db.commit()
            
            await i.followup.send(f"✅ Rascunho publicado com sucesso em {t_msg.thread.mention}!")
        except Exception as e:
            await i.followup.send(f"Erro ao criar thread: {e}")

    @app_commands.command(name="quest_atribuir", description="🔒 (Mestre) Força entrada de jogador em quest")
    @app_commands.autocomplete(quest_id=ac_quest_ativa)
    @app_commands.check(is_mestre)
    async def atribuir(self, i: discord.Interaction, quest_id: str, jogador: discord.Member):
        try: q_id = int(quest_id)
        except: return
        
        await self.bot.db.execute("INSERT OR IGNORE INTO quest_participantes (quest_id, user_id) VALUES (?,?)", (q_id, jogador.id))
        await self.bot.db.execute("UPDATE quests SET status='Em Andamento' WHERE id=?", (q_id,))
        await self.bot.db.commit()
        
        async with self.bot.db.execute("SELECT thread_id FROM quests WHERE id=?", (q_id,)) as c:
            row = await c.fetchone()
            if row and row[0]:
                try:
                    th = i.guild.get_thread(row[0])
                    if th: await th.send(f"🛡️ **{jogador.display_name}** foi adicionado à missão pelo Mestre.")
                except: pass
        
        await i.response.send_message(f"✅ {jogador.display_name} adicionado à Quest {q_id}.")

    @app_commands.command(name="memoria_importar", description="🔒 (Mestre) Upload de TXT para Lore")
    @app_commands.check(is_mestre)
    async def import_lore(self, i: discord.Interaction, arquivo: discord.Attachment):
        if not arquivo.filename.endswith('.txt'): return await i.response.send_message("Apenas .txt", ephemeral=True)
        await i.response.defer()
        try:
            txt = (await arquivo.read()).decode('utf-8')[:6000] 
            await self.bot.db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Resumo', ?)", (txt,))
            await self.bot.db.commit()
            await i.followup.send(f"✅ {len(txt)} caracteres importados para a memória.")
        except Exception as e: await i.followup.send(f"Erro: {e}")

    @app_commands.command(name="quest_concluir", description="🔒 (Mestre) Finaliza missão")
    @app_commands.autocomplete(quest_id=ac_quest_ativa)
    @app_commands.check(is_mestre)
    async def concluir(self, i: discord.Interaction, quest_id: str):
        try: q_id = int(quest_id)
        except: return
        
        db = self.bot.db
        async with db.execute("SELECT titulo, descricao, recompensa_ouro, recompensa_xp, thread_id FROM quests WHERE id=?", (q_id,)) as c:
            q = await c.fetchone()
        
        if not q: return await i.response.send_message("Erro.", ephemeral=True)
        tit, desc, gp, xp, tid = q

        async with db.execute("SELECT user_id FROM quest_participantes WHERE quest_id=?", (q_id,)) as c:
            parts = await c.fetchall()
        
        names = []
        for (uid,) in parts:
            async with db.execute("SELECT xp_atual, nivel, hp_max, hp_atual, ataque, ouro FROM personagens WHERE user_id=?", (uid,)) as c:
                char = await c.fetchone()
            if char:
                cxp, cniv, chpm, chpa, catk, cgp = char
                ngp = cgp + gp
                nxp = cxp + xp
                while True:
                    req = cniv * 1000
                    if nxp >= req: nxp-=req; cniv+=1; chpm+=5; chpa+=5; catk+=1
                    else: break
                await db.execute("UPDATE personagens SET xp_atual=?, nivel=?, hp_max=?, hp_atual=?, ataque=?, ouro=? WHERE user_id=?", (nxp, cniv, chpm, chpa, catk, ngp, uid))
                m = i.guild.get_member(uid)
                names.append(m.display_name if m else str(uid))

        await db.execute("UPDATE quests SET status='Concluida' WHERE id=?", (q_id,))
        mem = f"Conclusão da missão '{tit}': {desc[:100]}... Realizada por {', '.join(names)}."
        await db.execute("INSERT INTO memoria_campanha (tipo, conteudo) VALUES ('Conclusão', ?)", (mem,))
        await db.commit()

        if tid:
            try:
                th = i.guild.get_thread(tid)
                await th.send(f"🏆 **MISSÃO CUMPRIDA!**\nJogadores recompensados.")
                await th.edit(locked=True, archived=True, name=f"[✔] {tit}")
            except: pass
        
        await i.response.send_message("✅ Finalizado com sucesso.")

# ESTA É A FUNÇÃO QUE FALTAVA
async def setup(bot):
    await bot.add_cog(Quests(bot))