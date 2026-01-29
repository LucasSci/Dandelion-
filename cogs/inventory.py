import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands, ui

DB_NAME = "bestiario.db"

# =====================
# VIEW — INVENTÁRIO
# =====================

class InventarioView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Este inventário não é seu.", ephemeral=True)
            return False
        return True

    @ui.button(label="Vender Item (Primeiro)", emoji="💰", style=discord.ButtonStyle.success)
    async def vender_item(self, interaction: discord.Interaction, button: ui.Button):
        # A View não tem acesso direto ao bot, mas podemos pegar da interaction.client
        db = interaction.client.db

        async with db.execute("""
            SELECT id, nome, valor
            FROM inventario
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 1
        """, (self.user_id,)) as cursor:
            item = await cursor.fetchone()

        if not item:
            return await interaction.response.send_message(
                "🎒 Seu inventário está vazio.", ephemeral=True
            )

        item_id, nome, valor = item

        await db.execute("DELETE FROM inventario WHERE id = ?", (item_id,))

        # Atualiza o ouro do personagem
        await db.execute(
            "UPDATE personagens SET ouro = ouro + ? WHERE user_id = ?",
            (valor, self.user_id)
        )
        await db.commit()

        await interaction.response.send_message(
            f"✅ Você vendeu **{nome}** por 💰 {valor} ouros!",
            ephemeral=True
        )
        self.stop()

    @ui.button(label="Fechar", emoji="❌", style=discord.ButtonStyle.danger)
    async def fechar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.stop()


# =====================
# COG — INVENTORY
# =====================

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventario", description="🎒 Exibe seu inventário")
    async def inventario(self, interaction: discord.Interaction):
        async with self.bot.db.execute("""
            SELECT nome, tipo, valor
            FROM inventario
            WHERE user_id = ?
        """, (interaction.user.id,)) as cursor:
            itens = await cursor.fetchall()

        if not itens:
            return await interaction.response.send_message(
                "🎒 Seu inventário está vazio.", ephemeral=True
            )

        descricao = ""
        for nome, tipo, valor in itens:
            descricao += f"• **{nome}** ({tipo}) — 💰 {valor}\n"

        embed = discord.Embed(title="🎒 Inventário", description=descricao, color=0x2b2d31)
        
        view = InventarioView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Inventory(bot))