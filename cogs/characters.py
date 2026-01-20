import aiosqlite
import discord
import io
import json
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

    async def localizacao_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute(
            "SELECT nome FROM world_locations WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f'%{current}%',)
        ) as cursor:
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

    # --- LOCALIZACAO / MUNDO ---
    @app_commands.command(name="localizacao", description="Mostra a localização atual do personagem")
    async def localizacao(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user

        async with self.bot.db.execute("""
            SELECT p.nome, w.nome
            FROM personagens p
            LEFT JOIN world_locations w ON w.id = p.localizacao_id
            WHERE p.user_id = ?
        """, (target.id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem, local = row
        local = local or "Desconhecida"
        await interaction.response.send_message(f"📍 **{personagem}** está em **{local}**.")

    @app_commands.command(name="viajar", description="Define a localização atual do personagem")
    @app_commands.autocomplete(destino=localizacao_autocomplete)
    async def viajar(self, interaction: discord.Interaction, destino: str, usuario: discord.Member = None):
        if usuario and not is_mestre(interaction):
            return await interaction.response.send_message("❌ Apenas o Mestre pode mover outros jogadores.", ephemeral=True)

        target = usuario or interaction.user

        async with self.bot.db.execute("SELECT id FROM world_locations WHERE nome = ?", (destino,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return await interaction.response.send_message("❌ Localização não encontrada.", ephemeral=True)

        local_id = row[0]

        cursor = await self.bot.db.execute(
            "UPDATE personagens SET localizacao_id = ? WHERE user_id = ?",
            (local_id, target.id)
        )
        await self.bot.db.commit()

        if cursor.rowcount == 0:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        if target.id == interaction.user.id:
            await interaction.response.send_message(f"🧭 Você viajou para **{destino}**.")
        else:
            await interaction.response.send_message(f"🧭 {target.display_name} foi movido para **{destino}**.")

    @app_commands.command(name="ficha_exportar", description="📤 Exporta a ficha em JSON.")
    async def ficha_exportar(
        self, interaction: discord.Interaction, usuario: discord.Member = None
    ):
        target = usuario or interaction.user

        async with self.bot.db.execute(
            """
            SELECT id, nome, raca, classe, nivel, xp_atual, historia, imagem_url, ouro,
                   hp_max, hp_atual, mp_max, ataque, defesa
            FROM personagens WHERE user_id = ?
            """,
            (target.id,),
        ) as cursor:
            personagem = await cursor.fetchone()

        if not personagem:
            return await interaction.response.send_message(
                "❌ Nenhuma ficha encontrada.", ephemeral=True
            )

        personagem_id = personagem[0]
        async with self.bot.db.execute(
            "SELECT nome, descricao, dado FROM habilidades_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            habilidades = await cursor.fetchall()

        async with self.bot.db.execute(
            "SELECT nome, tipo, valor, efeito FROM inventario WHERE user_id = ?",
            (target.id,),
        ) as cursor:
            itens = await cursor.fetchall()

        ficha = {
            "nome": personagem[1],
            "raca": personagem[2],
            "classe": personagem[3],
            "nivel": personagem[4],
            "xp_atual": personagem[5],
            "historia": personagem[6],
            "imagem_url": personagem[7],
            "ouro": personagem[8],
            "atributos": {
                "hp_max": personagem[9],
                "hp_atual": personagem[10],
                "mp_max": personagem[11],
                "ataque": personagem[12],
                "defesa": personagem[13],
            },
            "habilidades": [
                {"nome": h[0], "descricao": h[1], "dado": h[2]} for h in habilidades
            ],
            "inventario": [
                {"nome": i[0], "tipo": i[1], "valor": i[2], "efeito": i[3]} for i in itens
            ],
        }

        conteúdo = json.dumps(ficha, ensure_ascii=False, indent=2)
        buffer = io.StringIO(conteúdo)
        arquivo = discord.File(buffer, filename=f"ficha_{target.display_name}.json")
        await interaction.response.send_message(
            "✅ Ficha exportada.", file=arquivo, ephemeral=True
        )

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
            SELECT p.id, p.nome, p.raca, p.classe, p.nivel, p.historia, p.imagem_url,
                   p.ouro, p.hp_atual, p.hp_max, p.vigor_atual, p.vigor_max,
                   p.toxicidade_atual, p.toxicidade_max, p.ataque, p.defesa, p.mp_max,
                   w.nome
            FROM personagens p
            LEFT JOIN world_locations w ON w.id = p.localizacao_id
            WHERE p.user_id = ?
        """, (target.id,)) as cursor:
            res = await cursor.fetchone()
        
        if not res:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        (
            char_id, nome, raca, classe, nivel, historia, img, ouro, hp_atual, hp_max,
            vigor_atual, vigor_max, toxicidade_atual, toxicidade_max, ataque, defesa, mp_max, local
        ) = res
        if hp_atual is None: hp_atual = hp_max
        if vigor_atual is None: vigor_atual = vigor_max

        embed = discord.Embed(
            title=f"📜 {nome}",
            description=historia or "Sem registro.",
            color=0xE8D6B3
        )
        embed.add_field(name="Raça", value=raca, inline=True)
        embed.add_field(name="Classe", value=classe, inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="📍 Localização", value=local or "Desconhecida", inline=False)
        
        pct = hp_atual / hp_max if hp_max > 0 else 0
        barra_vida = "🟩" * int(pct * 10) + "⬛" * (10 - int(pct * 10))
        embed.add_field(name="❤️ Vida (HP)", value=f"{hp_atual}/{hp_max}\n`{barra_vida}`", inline=False)

        pct_vigor = vigor_atual / vigor_max if vigor_max else 0
        barra_vigor = "🟨" * int(pct_vigor * 10) + "⬛" * (10 - int(pct_vigor * 10))
        embed.add_field(name="⚡ Vigor", value=f"{vigor_atual}/{vigor_max}\n`{barra_vigor}`", inline=True)
        embed.add_field(name="☠️ Toxicidade", value=f"{toxicidade_atual}/{toxicidade_max}", inline=True)
        embed.add_field(name="⚔️ Combate", value=f"Ataque {ataque} • Defesa {defesa}", inline=True)
        embed.add_field(name="✨ Magia", value=f"MP {mp_max}", inline=True)
        
        embed.add_field(name="Ouro", value=f"💰 {ouro}", inline=True)
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
