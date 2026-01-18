import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands
from ui.modals import CriarFichaModal
from ui.sheet_view import FichaView

DB_NAME = "bestiario.db"

def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- AUTOCOMPLETES ---
    async def personagens_disponiveis_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute("SELECT nome FROM personagens WHERE user_id IS NULL AND nome LIKE ? LIMIT 25", (f'%{current}%',)) as cursor:
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def meus_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute("SELECT nome FROM personagens WHERE user_id = ? AND nome LIKE ? LIMIT 25", (interaction.user.id, f'%{current}%')) as cursor:
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def todos_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute("SELECT nome FROM personagens WHERE nome LIKE ? LIMIT 25", (f'%{current}%',)) as cursor:
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    # --- COMANDOS DE MESTRE (XP, NÍVEL E OURO) ---

    @app_commands.command(name="mestre_add_xp", description="🔒 (Mestre) Dá XP ao jogador e processa Level Up")
    @app_commands.check(is_mestre)
    async def mestre_add_xp(self, interaction: discord.Interaction, usuario: discord.Member, xp: int):
        await interaction.response.defer()
        
        db = self.bot.db
        async with db.execute("SELECT nivel, xp_atual, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?", (usuario.id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados:
            return await interaction.followup.send("❌ Esse usuário não tem ficha.", ephemeral=True)

        nivel, xp_atual, hp_max, hp_atual, ataque = dados
        if hp_atual is None: hp_atual = hp_max

        xp_atual += xp
        niveis_subidos = 0
        
        while True:
            xp_necessario = nivel * 1000
            if xp_atual >= xp_necessario:
                xp_atual -= xp_necessario
                nivel += 1
                hp_max += 5
                hp_atual += 5 
                ataque += 1
                niveis_subidos += 1
            else:
                break
        
        await db.execute("""
            UPDATE personagens 
            SET nivel=?, xp_atual=?, hp_max=?, hp_atual=?, ataque=? 
            WHERE user_id=?
        """, (nivel, xp_atual, hp_max, hp_atual, ataque, usuario.id))
        await db.commit()

        msg = f"✨ **{usuario.display_name}** ganhou {xp} XP!"
        if niveis_subidos > 0:
            msg += f"\n🎉 **LEVEL UP!** Subiu {niveis_subidos} nível(is)!\nAgora Nível **{nivel}** (HP: {hp_max}, Atk: {ataque})"
        else:
            msg += f"\nXP Atual: {xp_atual}/{nivel*1000}"

        await interaction.followup.send(msg)

    @app_commands.command(name="mestre_levelup", description="🔒 (Mestre) Força a subida de 1 nível")
    @app_commands.check(is_mestre)
    async def mestre_levelup(self, interaction: discord.Interaction, usuario: discord.Member):
        db = self.bot.db
        async with db.execute("SELECT nivel, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?", (usuario.id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados: return await interaction.response.send_message("❌ Sem ficha.", ephemeral=True)
        
        nivel, hp_max, hp_atual, ataque = dados
        if hp_atual is None: hp_atual = hp_max

        novo_nivel = nivel + 1
        novo_hp = hp_max + 5
        novo_hp_atual = hp_atual + 5
        novo_ataque = ataque + 1

        await db.execute("""
            UPDATE personagens SET nivel=?, hp_max=?, hp_atual=?, ataque=? WHERE user_id=?
        """, (novo_nivel, novo_hp, novo_hp_atual, novo_ataque, usuario.id))
        await db.commit()

        await interaction.response.send_message(f"🆙 **{usuario.display_name}** foi promovido para o Nível **{novo_nivel}**!\n(+5 HP, +1 Atk)")

    @app_commands.command(name="mestre_leveldown", description="🔒 (Mestre) Remove 1 nível (corrige erro)")
    @app_commands.check(is_mestre)
    async def mestre_leveldown(self, interaction: discord.Interaction, usuario: discord.Member):
        db = self.bot.db
        async with db.execute("SELECT nivel, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?", (usuario.id,)) as cursor:
            dados = await cursor.fetchone()
        
        if not dados: return await interaction.response.send_message("❌ Sem ficha.", ephemeral=True)

        nivel, hp_max, hp_atual, ataque = dados
        if hp_atual is None: hp_atual = hp_max

        if nivel <= 1:
            return await interaction.response.send_message("❌ O personagem já está no nível 1.", ephemeral=True)

        novo_nivel = nivel - 1
        novo_hp = max(1, hp_max - 5)
        novo_hp_atual = min(hp_atual, novo_hp) 
        novo_ataque = max(1, ataque - 1)

        await db.execute("""
            UPDATE personagens SET nivel=?, hp_max=?, hp_atual=?, ataque=? WHERE user_id=?
        """, (novo_nivel, novo_hp, novo_hp_atual, novo_ataque, usuario.id))
        await db.commit()

        await interaction.response.send_message(f"🔻 **{usuario.display_name}** retornou para o Nível **{novo_nivel}**.\nStatus revertidos.")

    # --- NOVO COMANDO: GERENCIAR OURO ---
    @app_commands.command(name="mestre_ouro", description="🔒 (Mestre) Adiciona ou remove ouro (Use negativo para remover)")
    @app_commands.check(is_mestre)
    async def mestre_ouro(self, interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
        db = self.bot.db
        async with db.execute("SELECT ouro FROM personagens WHERE user_id = ?", (usuario.id,)) as cursor:
            dados = await cursor.fetchone()

        if not dados:
            return await interaction.response.send_message("❌ Esse usuário não tem ficha.", ephemeral=True)

        ouro_atual = dados[0]
        # Garante que o ouro não fique negativo
        novo_ouro = max(0, ouro_atual + quantidade)

        await db.execute("UPDATE personagens SET ouro = ? WHERE user_id = ?", (novo_ouro, usuario.id))
        await db.commit()

        if quantidade > 0:
            await interaction.response.send_message(f"💰 **{usuario.display_name}** recebeu **{quantidade}** moedas de ouro!\n(Total: {novo_ouro})")
        else:
            perda = abs(quantidade)
            await interaction.response.send_message(f"💸 **{usuario.display_name}** perdeu **{perda}** moedas de ouro.\n(Total: {novo_ouro})")

    # --- COMANDOS PADRÃO ---

    @app_commands.command(name="criar_ficha", description="Crie seu personagem")
    async def criar_ficha(self, interaction: discord.Interaction):
        async with self.bot.db.execute("SELECT nome FROM personagens WHERE user_id = ?", (interaction.user.id,)) as cursor:
            if await cursor.fetchone():
                return await interaction.response.send_message("❌ Você já tem um personagem! Use `/devolver_ficha` antes.", ephemeral=True)
        await interaction.response.send_modal(CriarFichaModal(target_user_id='proprio'))

    @app_commands.command(name="mestre_criar", description="🔒 (Mestre) Cria ficha")
    @app_commands.check(is_mestre)
    async def mestre_criar(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target_id = usuario.id if usuario else None
        await interaction.response.send_modal(CriarFichaModal(target_user_id=target_id))

    @app_commands.command(name="assumir_personagem", description="Pegue uma ficha do Pool")
    @app_commands.autocomplete(nome_personagem=personagens_disponiveis_autocomplete)
    async def assumir_personagem(self, interaction: discord.Interaction, nome_personagem: str):
        async with self.bot.db.execute("SELECT id FROM personagens WHERE user_id = ?", (interaction.user.id,)) as cursor:
            if await cursor.fetchone():
                return await interaction.response.send_message("❌ Você já tem um personagem!", ephemeral=True)

        cursor = await self.bot.db.execute("UPDATE personagens SET user_id = ? WHERE nome = ? AND user_id IS NULL", (interaction.user.id, nome_personagem))
        await self.bot.db.commit()

        if cursor.rowcount > 0:
            await interaction.response.send_message(f"⚔️ Agora você é **{nome_personagem}**! Use `/ficha` para ver o painel.")
        else:
            await interaction.response.send_message("❌ Erro ao assumir ficha.", ephemeral=True)

    @app_commands.command(name="devolver_ficha", description="Devolve ficha ao Pool")
    @app_commands.autocomplete(nome_personagem=meus_personagens_autocomplete)
    async def devolver_ficha(self, interaction: discord.Interaction, nome_personagem: str):
        cursor = await self.bot.db.execute("UPDATE personagens SET user_id = NULL WHERE user_id = ? AND nome = ?", (interaction.user.id, nome_personagem))
        await self.bot.db.commit()
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"👋 Você devolveu **{nome_personagem}** ao Pool.")
        else:
            await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

    @app_commands.command(name="mestre_vincular", description="🔒 (Mestre) Transfere ficha")
    @app_commands.check(is_mestre)
    @app_commands.autocomplete(nome_personagem=todos_personagens_autocomplete)
    async def mestre_vincular(self, interaction: discord.Interaction, nome_personagem: str, usuario: discord.Member):
        await self.bot.db.execute("UPDATE personagens SET user_id = NULL WHERE user_id = ?", (usuario.id,))
        cursor = await self.bot.db.execute("UPDATE personagens SET user_id = ? WHERE nome = ?", (usuario.id, nome_personagem))
        await self.bot.db.commit()
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ **{nome_personagem}** vinculado a {usuario.mention}.")
        else:
            await interaction.response.send_message("❌ Erro ao vincular.", ephemeral=True)

    # --- COMANDO FICHA (O PAINEL INTERATIVO) ---
    @app_commands.command(name="ficha", description="Abre o painel interativo do personagem")
    async def ficha(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        
        async with self.bot.db.execute("""
            SELECT id, nome, raca, classe, nivel, historia, imagem_url, ouro, hp_atual, hp_max
            FROM personagens WHERE user_id = ?
        """, (target.id,)) as cursor:
            res = await cursor.fetchone()
        
        if not res:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        char_id, nome, raca, classe, nivel, historia, img, ouro, hp_atual, hp_max = res
        if hp_atual is None: hp_atual = hp_max

        embed = discord.Embed(title=f"📜 {nome}", color=0x2b2d31)
        embed.add_field(name="Raça", value=raca)
        embed.add_field(name="Classe", value=classe)
        embed.add_field(name="Nível", value=str(nivel))
        
        pct = hp_atual / hp_max if hp_max > 0 else 0
        barra_vida = "🟩" * int(pct * 10) + "⬛" * (10 - int(pct * 10))
        embed.add_field(name="❤️ Vida (HP)", value=f"{hp_atual}/{hp_max}\n`{barra_vida}`", inline=False)
        
        embed.add_field(name="Ouro", value=f"💰 {ouro}")
        embed.description = historia or "Sem registro."
        if img: embed.set_thumbnail(url=img)
        
        view = FichaView(personagem_id=char_id, user_id_dono=target.id)
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="listar_fichas", description="Lista todas as fichas")
    async def listar_fichas(self, interaction: discord.Interaction):
         # Otimização: LIMIT 20 para evitar carregar todas as fichas desnecessariamente
         async with self.bot.db.execute("SELECT nome, user_id FROM personagens LIMIT 20") as cursor:
            rows = await cursor.fetchall()
         if not rows: return await interaction.response.send_message("📭 Nenhuma ficha.", ephemeral=True)
         txt = "\n".join([f"• {r[0]} ({'Ocupado' if r[1] else 'Livre'})" for r in rows])
         await interaction.response.send_message(f"**Fichas:**\n{txt}")

async def setup(bot):
    await bot.add_cog(Characters(bot))