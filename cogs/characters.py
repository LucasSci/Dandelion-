import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands
from ui.modals import CriarFichaModal
from ui.sheet_view import FichaView  # <--- IMPORTANDO A NOVA VIEW

DB_NAME = "bestiario.db"

def is_mestre(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator

class Characters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- AUTOCOMPLETES (Iguais) ---
    async def personagens_disponiveis_autocomplete(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT nome FROM personagens WHERE user_id IS NULL AND nome LIKE ? LIMIT 25", (f'%{current}%',))
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def meus_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT nome FROM personagens WHERE user_id = ? AND nome LIKE ? LIMIT 25", (interaction.user.id, f'%{current}%'))
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def todos_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT nome FROM personagens WHERE nome LIKE ? LIMIT 25", (f'%{current}%',))
            rows = await cursor.fetchall()
            return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    # --- COMANDOS ---

    @app_commands.command(name="criar_ficha", description="Crie seu personagem")
    async def criar_ficha(self, interaction: discord.Interaction):
        # Lógica de criação mantém-se igual
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT nome FROM personagens WHERE user_id = ?", (interaction.user.id,)) as cursor:
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
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT id FROM personagens WHERE user_id = ?", (interaction.user.id,))
            if await cursor.fetchone():
                return await interaction.response.send_message("❌ Você já tem um personagem!", ephemeral=True)
            
            cursor = await db.execute("UPDATE personagens SET user_id = ? WHERE nome = ? AND user_id IS NULL", (interaction.user.id, nome_personagem))
            await db.commit()
            
            if cursor.rowcount > 0:
                await interaction.response.send_message(f"⚔️ Agora você é **{nome_personagem}**! Use `/ficha` para ver o painel.")
            else:
                await interaction.response.send_message("❌ Erro ao assumir ficha.", ephemeral=True)

    @app_commands.command(name="devolver_ficha", description="Devolve ficha ao Pool")
    @app_commands.autocomplete(nome_personagem=meus_personagens_autocomplete)
    async def devolver_ficha(self, interaction: discord.Interaction, nome_personagem: str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("UPDATE personagens SET user_id = NULL WHERE user_id = ? AND nome = ?", (interaction.user.id, nome_personagem))
            await db.commit()
            if cursor.rowcount > 0:
                await interaction.response.send_message(f"👋 Você devolveu **{nome_personagem}** ao Pool.")
            else:
                await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

    @app_commands.command(name="mestre_vincular", description="🔒 (Mestre) Transfere ficha")
    @app_commands.check(is_mestre)
    @app_commands.autocomplete(nome_personagem=todos_personagens_autocomplete)
    async def mestre_vincular(self, interaction: discord.Interaction, nome_personagem: str, usuario: discord.Member):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE personagens SET user_id = NULL WHERE user_id = ?", (usuario.id,))
            cursor = await db.execute("UPDATE personagens SET user_id = ? WHERE nome = ?", (usuario.id, nome_personagem))
            await db.commit()
            if cursor.rowcount > 0:
                await interaction.response.send_message(f"✅ **{nome_personagem}** vinculado a {usuario.mention}.")
            else:
                await interaction.response.send_message("❌ Erro ao vincular.", ephemeral=True)

    # --- COMANDO FICHA (O PAINEL INTERATIVO) ---
    @app_commands.command(name="ficha", description="Abre o painel interativo do personagem")
    async def ficha(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        
        async with aiosqlite.connect(DB_NAME) as db:
            # Pegamos o ID da ficha além dos dados visuais
            async with db.execute("""
                SELECT id, nome, raca, classe, nivel, historia, imagem_url, ouro 
                FROM personagens WHERE user_id = ?
            """, (target.id,)) as cursor:
                res = await cursor.fetchone()
        
        if not res:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        char_id, nome, raca, classe, nivel, historia, img, ouro = res

        # Embed Inicial (Modo Info)
        embed = discord.Embed(title=f"📜 {nome}", color=0x2b2d31)
        embed.add_field(name="Raça", value=raca)
        embed.add_field(name="Classe", value=classe)
        embed.add_field(name="Nível", value=str(nivel))
        embed.add_field(name="Ouro", value=f"💰 {ouro}")
        embed.description = historia or "Sem registro."
        if img: embed.set_thumbnail(url=img)
        
        # Cria a View interativa passando o ID da ficha e o dono
        view = FichaView(personagem_id=char_id, user_id_dono=target.id)
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="listar_fichas", description="Lista todas as fichas")
    async def listar_fichas(self, interaction: discord.Interaction):
         async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT nome, user_id FROM personagens") as cursor:
                rows = await cursor.fetchall()
         if not rows: return await interaction.response.send_message("📭 Nenhuma ficha.", ephemeral=True)
         txt = "\n".join([f"• {r[0]} ({'Ocupado' if r[1] else 'Livre'})" for r in rows[:20]])
         await interaction.response.send_message(f"**Fichas:**\n{txt}")

async def setup(bot):
    await bot.add_cog(Characters(bot))