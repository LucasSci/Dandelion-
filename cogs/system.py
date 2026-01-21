import platform
from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


@dataclass(frozen=True)
class HealthCheck:
    ok: bool
    detail: str


class System(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.started_at = datetime.now(timezone.utc)

    async def _check_database(self) -> HealthCheck:
        if not getattr(self.bot, "db", None):
            return HealthCheck(False, "Banco indisponível.")

        try:
            async with self.bot.db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            return HealthCheck(True, "Banco OK.")
        except Exception:
            return HealthCheck(False, "Banco com erro.")

    @app_commands.command(name="status", description="Mostra o status do bot e integrações.")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        db_health = await self._check_database()
        latency_ms = round(self.bot.latency * 1000, 2)
        uptime = datetime.now(timezone.utc) - self.started_at

        embed = discord.Embed(
            title="🛠️ Status do Dandelion",
            color=0x2b2d31,
        )
        embed.add_field(name="Latência", value=f"{latency_ms}ms", inline=True)
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=True)
        embed.add_field(name="Servidor Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Banco", value=db_health.detail, inline=True)
        embed.add_field(name="Guildas", value=str(len(self.bot.guilds)), inline=True)
        embed.set_footer(text="Monitoramento rápido do sistema.")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(System(bot))
