import discord
import aiosqlite
import random
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
from scripts.contract_gen import gerar_imagem_contrato
import logging

log = logging.getLogger(__name__)

# ==============================================================================
# VIEW DO FÓRUM (Botão de Aceitar)
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

    @ui.button(label="Aceitar Contrato", style=discord.ButtonStyle.success, emoji="✍️", custom_id="quest_btn_aceitar")
    async def btn_aceitar(self, interaction: discord.Interaction, button: ui.Button):
        thread_id = interaction.channel_id
        
        # Busca Quest
        query = "SELECT id, titulo, descricao, recompensa_ouro, recompensa_xp, status, classes_req, regiao, max_jogadores, alvo_monstro_nome, imagem_url FROM quests WHERE thread_id=?"
        async with self.db.execute(query, (thread_id,)) as c: q = await c.fetchone()
        
        if not q: return await interaction.response.send_message("❌ Quest não encontrada/inválida.", ephemeral=True)
        q_id, _, _, _, _, status, req, q_regiao, max_p, _, _ = q

        if status == "Rascunho": return await interaction.response.send_message("🚧 Esta missão ainda é um rascunho.", ephemeral=True)
        if status == "Concluida": return await interaction.response.send_message("🏁 Encerrada.", ephemeral=True)

        # Checa Localização do Jogador
        async with self.db.execute("SELECT localizacao_atual, classe FROM personagens WHERE user_id=?", (interaction.user.id,)) as c:
            char = await c.fetchone()
        
        if not char: return await interaction.response.send_message("❌ Crie ficha primeiro (`/criar_ficha`).", ephemeral=True)
        p_local, p_classe = char

        # Lógica de Viagem: O jogador DEVE estar no local para aceitar
        # Mas a quest pode ter sido gerada em qualquer lugar.
        if q_regiao and q_regiao != "Desconhecido" and p_local != q_regiao:
            return await interaction.response.send_message(f"🚫 **Você está longe!**\nEsta missão é em **{q_regiao}**, mas você está em **{p_local}**.\nViaje até lá (`/viajar {q_regiao}`) para encontrar o contratante e aceitar a missão.", ephemeral=True)

        # Checa Participantes
        async with self.db.execute("SELECT user_id FROM quest_participantes WHERE quest_id=?", (q_id,)) as c:
            rows = await c.fetchall()
            parts = [r[0] for r in rows]

        if interaction.user.id in parts: return await interaction.response.send_message("⚠️ Já está inscrito.", ephemeral=True)
        if len(parts) >= max_p: return await interaction.response.send_message("🚫 Cheio.", ephemeral=True)

        # Checa Classe
        p_cls = p_classe.lower() if p_classe else "nenhuma"
        allowed = [x.strip().lower() for x in req.split(',')]
        if "todas" not in allowed and p_cls not in allowed:
            return await interaction.response.send_message(f"🚫 Classe {p_classe} não permitida.", ephemeral=True)

        # Insere e Atualiza
        await self.db.execute("INSERT INTO quest_participantes (quest_id, user_id) VALUES (?,?)", (q_id, interaction.user.id))
        
        if status == "Disponivel":
            await self.db.execute("UPDATE quests SET status='Em Andamento' WHERE id=?", (q_id,))
            q = list(q); q[5] = "Em Andamento"; q = tuple(q)
        
        await self.db.commit()
        
        parts.append(interaction.user.id)
        new_emb = await self.update_embed(interaction, q, parts)
        
        await interaction.response.edit_message(embed=new_emb, view=self)
        await interaction.followup.send(f"✅ {interaction.user.mention} pegou o contrato! Boa sorte.", ephemeral=False)

# ==============================================================================
# COG PRINCIPAL
# ==============================================================================

class Quests(commands.Cog):
    def __init__(self, bot): self.bot = bot
    
    # Registra a view persistente
    async def cog_load(self): self.bot.add_view(QuestPostView(self.bot.db))

    def is_mestre(i: discord.Interaction): return i.user.guild_permissions.administrator

    # Autocomplete de Regiões (Puxa do Banco agora!)
    async def regioes_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute("SELECT nome FROM locais_mundo WHERE nome LIKE ? LIMIT 25", (f'%{current}%',)) as c:
            rows = await c.fetchall()
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    # --- COMANDOS ---

    @app_commands.command(name="quest_gerar", description="✨ Gera uma missão global ou em região específica.")
    @app_commands.describe(regiao_alvo="Deixe vazio para uma região aleatória do mundo.")
    @app_commands.autocomplete(regiao_alvo=regioes_autocomplete)
    @app_commands.check(is_mestre)
    async def quest_gerar(self, interaction: discord.Interaction, regiao_alvo: Optional[str] = None):
        """
        Gera uma missão. Se regiao_alvo não for informada, escolhe uma aleatória do mundo.
        """
        # Correção de Fórum
        target_forum = interaction.channel
        if isinstance(target_forum, discord.Thread): target_forum = target_forum.parent
        if not isinstance(target_forum, discord.ForumChannel):
            return await interaction.response.send_message("❌ Use em um Fórum.", ephemeral=True)

        await interaction.response.defer()

        # 1. Definir Região e Coordenadas
        if regiao_alvo:
            # Tenta pegar coordenadas da região informada
            async with self.bot.db.execute("SELECT nome, coord_x, coord_y FROM locais_mundo WHERE nome LIKE ?", (f'%{regiao_alvo}%',)) as c:
                loc_data = await c.fetchone()
        else:
            # Sorteia uma região do mundo
            async with self.bot.db.execute("SELECT nome, coord_x, coord_y FROM locais_mundo ORDER BY RANDOM() LIMIT 1") as c:
                loc_data = await c.fetchone()

        if not loc_data:
            # Fallback se o banco de locais estiver vazio
            regiao, cx, cy = "Desconhecido", 0, 0
        else:
            regiao, cx, cy = loc_data

        # 2. Chama a IA
        ai_cog = self.bot.get_cog("AIHandler")
        if not ai_cog: return await interaction.followup.send("❌ IA Offline.")

        try:
            # Passa a região selecionada/sorteada, não a do jogador
            if hasattr(ai_cog, 'gerar_quest_imersiva'):
                d = await ai_cog.gerar_quest_imersiva(regiao_atual=regiao, coordenadas=(cx, cy))
            else:
                d = await ai_cog.gerar_quest_cronologica("Média") # Fallback
        except Exception as e:
            return await interaction.followup.send(f"❌ Erro IA: {e}")

        if not d: return await interaction.followup.send("❌ Falha na geração.")

        # 3. Imagem
        file_contrato = None
        try:
            buf = await gerar_imagem_contrato(d['titulo'], d['descricao'], f"{d['ouro']}G")
            if buf: file_contrato = discord.File(buf, filename="contrato.png")
        except: pass

        # 4. Postar
        embed = discord.Embed(title=f"📜 [{regiao}] {d['titulo']}", description=d['descricao'], color=0x57F287)
        embed.add_field(name="🌍 Região", value=regiao, inline=True)
        embed.add_field(name="👹 Alvo", value=d['monstro'], inline=True)
        embed.add_field(name="💰 Recompensa", value=f"{d['ouro']}G | {d['xp']}XP", inline=True)
        
        files = [file_contrato] if file_contrato else []
        
        try:
            t_msg = await target_forum.create_thread(
                name=f"[{regiao}] {d['titulo']}", 
                embed=embed, 
                files=files, 
                view=QuestPostView(self.bot.db)
            )
            
            # Salva no DB
            await self.bot.db.execute("""
                INSERT INTO quests (titulo, descricao, recompensa_ouro, recompensa_xp, status, classes_req, 
                                    regiao, alvo_monstro_nome, imagem_url, thread_id, local_nome, coord_x, coord_y)
                VALUES (?, ?, ?, ?, 'Disponivel', 'Todas', ?, ?, ?, ?, ?, ?, ?)
            """, (d['titulo'], d['descricao'], d['ouro'], d['xp'], regiao, d['monstro'], None, t_msg.thread.id, regiao, cx, cy))
            await self.bot.db.commit()

            await t_msg.thread.send("⬇️ **Interessado neste contrato?**", view=QuestPostView(self.bot.db))
            await interaction.followup.send(f"✅ Contrato criado em **{regiao}**! {t_msg.thread.mention}")

        except Exception as e:
            log.error(f"Post error: {e}")
            await interaction.followup.send(f"❌ Erro ao postar: {e}")

async def setup(bot):
    await bot.add_cog(Quests(bot))