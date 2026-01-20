from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

ROADMAP_PATH = Path(__file__).resolve().parent.parent / "data" / "roadmap_features.json"


@dataclass(frozen=True)
class RoadmapCategory:
    name: str
    items: List[str]


def load_roadmap() -> Dict[str, RoadmapCategory]:
    with ROADMAP_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    roadmap: Dict[str, RoadmapCategory] = {}
    for name, items in payload.items():
        roadmap[name] = RoadmapCategory(name=name, items=list(items))
    return roadmap


class Roadmap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.roadmap = load_roadmap()

    async def categoria_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        choices: List[app_commands.Choice[str]] = []
        for name in self.roadmap.keys():
            if current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    @app_commands.command(name="roadmap", description="🧭 Exibe o roadmap de upgrades do Dandelion.")
    @app_commands.describe(categoria="Filtra por categoria (opcional)")
    @app_commands.autocomplete(categoria=categoria_autocomplete)
    async def roadmap_cmd(
        self, interaction: discord.Interaction, categoria: Optional[str] = None
    ):
        if categoria:
            categoria_data = self.roadmap.get(categoria)
            if not categoria_data:
                return await interaction.response.send_message(
                    "❌ Categoria não encontrada.", ephemeral=True
                )

            itens = "\n".join(f"• {item}" for item in categoria_data.items)
            embed = discord.Embed(
                title=f"🧭 Roadmap: {categoria_data.name}",
                description=itens,
                color=0x4C7C5E,
            )
            embed.set_footer(text=f"Total de upgrades: {len(categoria_data.items)}")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        categorias = []
        total_itens = 0
        for name, categoria_data in self.roadmap.items():
            total_itens += len(categoria_data.items)
            categorias.append(f"• {name} ({len(categoria_data.items)})")

        embed = discord.Embed(
            title="🧭 Roadmap de Upgrades",
            description="\n".join(categorias),
            color=0x4C7C5E,
        )
        embed.set_footer(text=f"Total de upgrades planejados: {total_itens}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roadmap(bot))
