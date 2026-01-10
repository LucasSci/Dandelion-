import sqlite3
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
            await interaction.response.send_message(
                "❌ Este inventário não é seu.",
                ephemeral=True
            )
            return False
        return True

    @ui.button(label="💰 Vender Item", style=discord.ButtonStyle.success)
    async def vender_item(self, interaction: discord.Interaction, button: ui.Button):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            item = cursor.execute("""
                SELECT id, nome, valor
                FROM inventario
                WHERE user_id = ?
                ORDER BY id ASC
                LIMIT 1
            """, (self.user_id,)).fetchone()

            if not item:
                return await interaction.response.send_message(
                    "🎒 Seu inventário está vazio.",
                    ephemeral=True
                )

            item_id, nome, valor = item

            cursor.execute(
                "DELETE FROM inventario WHERE id = ?",
                (item_id,)
            )

            cursor.execute(
                "UPDATE personagens SET ouro = ouro + ? WHERE user_id = ?",
                (valor, self.user_id)
            )

            conn.commit()

        await interaction.response.send_message(
            f"✅ Você vendeu **{nome}** por 💰 {valor} ouros!",
            ephemeral=True
        )

        self.stop()

    @ui.button(label="❌ Fechar", style=discord.ButtonStyle.danger)
    async def fechar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.stop()


# =====================
# COG — INVENTORY
# =====================

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="inventario",
        description="🎒 Exibe seu inventário"
    )
    async def inventario(self, interaction: discord.Interaction):
        with sqlite3.connect(DB_NAME) as conn:
            itens = conn.execute("""
                SELECT nome, tipo, valor
                FROM inventario
                WHERE user_id = ?
            """, (interaction.user.id,)).fetchall()

        if not itens:
            return await interaction.response.send_message(
                "🎒 Seu inventário está vazio.",
                ephemeral=True
            )

        descricao = ""
        for nome, tipo, valor in itens:
            descricao += f"• **{nome}** ({tipo}) — 💰 {valor}\n"

        embed = discord.Embed(
            title="🎒 Inventário",
            description=descricao,
            color=0x2b2d31
        )

        view = InventarioView(interaction.user.id)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
