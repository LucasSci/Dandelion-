from __future__ import annotations

import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


DEFAULT_BIOME = "Planície"
def _inferir_bioma_por_nome(nome: str | None) -> str:
    if not nome:
        return DEFAULT_BIOME
    nome_lower = nome.lower()
    if "pântano" in nome_lower or "pantano" in nome_lower:
        return "Pântano"
    if "floresta" in nome_lower or "bosque" in nome_lower:
        return "Floresta"
    if "caverna" in nome_lower or "gruta" in nome_lower:
        return "Caverna"
    if "cidade" in nome_lower or "vila" in nome_lower or "vilarejo" in nome_lower:
        return "Cidade"
    return DEFAULT_BIOME


class Alchemy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _obter_bioma_personagem(self, user_id: int) -> str:
        async with self.bot.db.execute(
            """
            SELECT w.biome, w.nome
            FROM personagens p
            LEFT JOIN world_locations w ON p.localizacao_id = w.id
            WHERE p.user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return DEFAULT_BIOME
        biome, nome = row
        return biome or _inferir_bioma_por_nome(nome)

    async def _selecionar_ingrediente_bioma(self, bioma: str) -> Optional[tuple]:
        async with self.bot.db.execute(
            """
            SELECT id, nome, tipo, raridade, qualidade_min, qualidade_max, descricao
            FROM alchemy_ingredients
            WHERE biome = ? OR biome = 'Qualquer' OR biome IS NULL
            """,
            (bioma,),
        ) as cursor:
            ingredientes = await cursor.fetchall()
        if not ingredientes:
            return None
        pesos = [max(1, 6 - (row[3] or 1)) for row in ingredientes]
        return random.choices(ingredientes, weights=pesos, k=1)[0]

    async def _atualizar_ingrediente_usuario(
        self, user_id: int, ingredient_id: int, quantidade: int, qualidade: int
    ) -> None:
        async with self.bot.db.execute(
            """
            SELECT quantidade, qualidade
            FROM alchemy_user_ingredients
            WHERE user_id = ? AND ingredient_id = ?
            """,
            (user_id, ingredient_id),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            qtd_atual, qual_atual = row
            nova_qtd = qtd_atual + quantidade
            nova_qual = int((qual_atual * qtd_atual + qualidade * quantidade) / nova_qtd)
            await self.bot.db.execute(
                """
                UPDATE alchemy_user_ingredients
                SET quantidade = ?, qualidade = ?, atualizado_em = datetime('now')
                WHERE user_id = ? AND ingredient_id = ?
                """,
                (nova_qtd, nova_qual, user_id, ingredient_id),
            )
        else:
            await self.bot.db.execute(
                """
                INSERT INTO alchemy_user_ingredients (user_id, ingredient_id, quantidade, qualidade)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, ingredient_id, quantidade, qualidade),
            )
        await self.bot.db.commit()

    async def _consumir_ingrediente(self, user_id: int, ingredient_id: int, quantidade: int) -> None:
        async with self.bot.db.execute(
            """
            SELECT quantidade
            FROM alchemy_user_ingredients
            WHERE user_id = ? AND ingredient_id = ?
            """,
            (user_id, ingredient_id),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return
        qtd_atual = row[0]
        novo = qtd_atual - quantidade
        if novo <= 0:
            await self.bot.db.execute(
                "DELETE FROM alchemy_user_ingredients WHERE user_id = ? AND ingredient_id = ?",
                (user_id, ingredient_id),
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE alchemy_user_ingredients
                SET quantidade = ?, atualizado_em = datetime('now')
                WHERE user_id = ? AND ingredient_id = ?
                """,
                (novo, user_id, ingredient_id),
            )

    async def _ajustar_toxicidade(self, user_id: int, valor: int) -> int:
        async with self.bot.db.execute(
            """
            SELECT toxicidade_atual, toxicidade_max
            FROM personagens WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return 0
        atual, maximo = row
        nova = min(maximo, atual + valor)
        await self.bot.db.execute(
            "UPDATE personagens SET toxicidade_atual = ? WHERE user_id = ?",
            (nova, user_id),
        )
        await self.bot.db.commit()
        return nova - atual

    async def _verificar_ficha(self, interaction: discord.Interaction) -> bool:
        async with self.bot.db.execute(
            "SELECT id FROM personagens WHERE user_id = ?", (interaction.user.id,)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def _autocomplete_receitas(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        async with self.bot.db.execute(
            "SELECT nome FROM alchemy_recipes WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [app_commands.Choice(name=row[0], value=row[0]) for row in rows]

    async def _listar_receitas_desbloqueadas(self, user_id: int) -> list[tuple]:
        async with self.bot.db.execute(
            """
            SELECT ar.id, ar.nome, ar.base_alcoolica, ar.efeito, ar.toxicidade_base, ar.qualidade_min, ur.unlocked_at
            FROM alchemy_user_recipes ur
            JOIN alchemy_recipes ar ON ar.id = ur.recipe_id
            WHERE ur.user_id = ?
            ORDER BY ar.nome
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()

    @app_commands.command(name="forage", description="🌿 Coleta ervas e ingredientes conforme o bioma.")
    async def forage(self, interaction: discord.Interaction):
        if not await self._verificar_ficha(interaction):
            return await interaction.response.send_message(
                "❌ Você precisa de uma ficha para coletar ingredientes.", ephemeral=True
            )
        bioma = await self._obter_bioma_personagem(interaction.user.id)
        ingrediente = await self._selecionar_ingrediente_bioma(bioma)
        if not ingrediente:
            return await interaction.response.send_message(
                "⚠️ Nenhum ingrediente disponível para este bioma.", ephemeral=True
            )
        ing_id, nome, tipo, _raridade, q_min, q_max, descricao = ingrediente
        quantidade = random.randint(1, 2)
        qualidade = random.randint(q_min or 40, q_max or 100)
        await self._atualizar_ingrediente_usuario(interaction.user.id, ing_id, quantidade, qualidade)

        desc_extra = f"\n📜 {descricao}" if descricao else ""
        await interaction.response.send_message(
            (
                f"🧺 Você coletou **{quantidade}x {nome}** ({tipo}) no bioma **{bioma}**.\n"
                f"Qualidade média: **{qualidade}**.{desc_extra}"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="alquimia_ingredientes", description="🧪 Lista seus ingredientes de alquimia.")
    async def listar_ingredientes(self, interaction: discord.Interaction):
        async with self.bot.db.execute(
            """
            SELECT ai.nome, ai.tipo, ui.quantidade, ui.qualidade
            FROM alchemy_user_ingredients ui
            JOIN alchemy_ingredients ai ON ai.id = ui.ingredient_id
            WHERE ui.user_id = ?
            ORDER BY ai.tipo, ai.nome
            """,
            (interaction.user.id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "🎒 Você ainda não possui ingredientes.", ephemeral=True
            )

        linhas = [
            f"• **{nome}** ({tipo}) — {quantidade}x (Qualidade {qualidade})"
            for nome, tipo, quantidade, qualidade in rows
        ]
        embed = discord.Embed(
            title="🧪 Ingredientes de Alquimia",
            description="\n".join(linhas),
            color=0x3b7a57,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="alquimia_receitas", description="📜 Lista receitas disponíveis.")
    async def listar_receitas(self, interaction: discord.Interaction):
        async with self.bot.db.execute(
            """
            SELECT id, nome, base_alcoolica, efeito, toxicidade_base, qualidade_min
            FROM alchemy_recipes
            ORDER BY nome
            """
        ) as cursor:
            receitas = await cursor.fetchall()

        if not receitas:
            return await interaction.response.send_message(
                "📭 Nenhuma receita registrada.", ephemeral=True
            )

        blocos = []
        for rec_id, nome, base, efeito, tox, qualidade_min in receitas:
            async with self.bot.db.execute(
                """
                SELECT ai.nome, ri.quantidade
                FROM alchemy_recipe_ingredients ri
                JOIN alchemy_ingredients ai ON ai.id = ri.ingredient_id
                WHERE ri.recipe_id = ?
                """,
                (rec_id,),
            ) as cursor:
                ingredientes = await cursor.fetchall()
            ingredientes_txt = ", ".join(
                f"{qtd}x {ing}" for ing, qtd in ingredientes
            ) or "—"
            blocos.append(
                (
                    f"**{nome}**\n"
                    f"Base: {base} | Toxicidade: {tox} | Qualidade mínima: {qualidade_min}\n"
                    f"Ingredientes: {ingredientes_txt}\n"
                    f"Efeito: {efeito}"
                )
            )

        embed = discord.Embed(
            title="📜 Grimório de Alquimia",
            description="\n\n".join(blocos)[:4000],
            color=0x4b7f52,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="alquimia_receitas_desbloqueadas",
        description="📘 Lista suas receitas de alquimia desbloqueadas.",
    )
    async def listar_receitas_desbloqueadas(self, interaction: discord.Interaction):
        receitas = await self._listar_receitas_desbloqueadas(interaction.user.id)
        if not receitas:
            return await interaction.response.send_message(
                "📭 Você ainda não desbloqueou receitas.", ephemeral=True
            )

        linhas = [
            (
                f"**{nome}** — Base: {base} | Toxicidade: {tox} | Qualidade mínima: {qual_min}\n"
                f"Efeito: {efeito}"
            )
            for _rec_id, nome, base, efeito, tox, qual_min, _unlocked_at in receitas
        ]

        embed = discord.Embed(
            title="📘 Receitas Conhecidas",
            description="\n\n".join(linhas)[:4000],
            color=0x4b7f52,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="alquimia_criar", description="⚗️ Cria uma poção a partir de uma receita.")
    @app_commands.describe(
        receita="Nome da receita",
        improvisar="Permite tentar sem ingredientes completos (gera toxicidade extra).",
    )
    @app_commands.autocomplete(receita=_autocomplete_receitas)
    async def criar_pocao(
        self, interaction: discord.Interaction, receita: str, improvisar: Optional[bool] = False
    ):
        if not await self._verificar_ficha(interaction):
            return await interaction.response.send_message(
                "❌ Você precisa de uma ficha para criar poções.", ephemeral=True
            )
        async with self.bot.db.execute(
            """
            SELECT id, nome, base_alcoolica, efeito, toxicidade_base, qualidade_min
            FROM alchemy_recipes
            WHERE nome LIKE ?
            """,
            (f"%{receita}%",),
        ) as cursor:
            rec = await cursor.fetchone()

        if not rec:
            return await interaction.response.send_message(
                "❌ Receita não encontrada.", ephemeral=True
            )

        rec_id, nome, base, efeito, tox_base, qualidade_min = rec
        async with self.bot.db.execute(
            "SELECT id FROM alchemy_ingredients WHERE nome = ?",
            (base,),
        ) as cursor:
            base_row = await cursor.fetchone()
        if not base_row:
            return await interaction.response.send_message(
                "⚠️ Receita inválida (base alcoólica não cadastrada).",
                ephemeral=True,
            )
        base_id = base_row[0]

        async with self.bot.db.execute(
            """
            SELECT ai.id, ai.nome, ri.quantidade, ui.quantidade, ui.qualidade
            FROM alchemy_recipe_ingredients ri
            JOIN alchemy_ingredients ai ON ai.id = ri.ingredient_id
            LEFT JOIN alchemy_user_ingredients ui
                ON ui.ingredient_id = ai.id AND ui.user_id = ?
            WHERE ri.recipe_id = ?
            """,
            (interaction.user.id, rec_id),
        ) as cursor:
            ingredientes = await cursor.fetchall()

        async with self.bot.db.execute(
            """
            SELECT quantidade, qualidade
            FROM alchemy_user_ingredients
            WHERE user_id = ? AND ingredient_id = ?
            """,
            (interaction.user.id, base_id),
        ) as cursor:
            base_inv = await cursor.fetchone()

        faltantes = []
        qualidade_total = 0
        peso_total = 0
        for ing_id, ing_nome, qtd_req, qtd_user, qualidade in ingredientes:
            if qtd_user is None or qtd_user < qtd_req:
                faltantes.append(f"{ing_nome} ({qtd_req}x)")
            else:
                qualidade_total += (qualidade or 0) * qtd_req
                peso_total += qtd_req

        if not base_inv or base_inv[0] < 1:
            faltantes.append(f"{base} (1x)")

        if faltantes and not improvisar:
            return await interaction.response.send_message(
                f"❌ Ingredientes faltando: {', '.join(faltantes)}.\n"
                "Use `improvisar=True` para arriscar.",
                ephemeral=True,
            )

        if faltantes and improvisar:
            tox_extra = await self._ajustar_toxicidade(interaction.user.id, tox_base + 15)
            return await interaction.response.send_message(
                (
                    "⚠️ Você errou a fórmula! A mistura falhou e liberou toxinas.\n"
                    f"Toxicidade +{tox_extra}. Ingredientes faltantes: {', '.join(faltantes)}."
                ),
                ephemeral=True,
            )

        media_qualidade = int(qualidade_total / peso_total) if peso_total else 0
        tox_total = tox_base
        colateral = ""
        if media_qualidade < qualidade_min:
            tox_total += 10
            colateral = (
                "\n⚠️ Ingredientes de baixa qualidade geraram efeitos colaterais."
            )

        await self._consumir_ingrediente(interaction.user.id, base_id, 1)
        for ing_id, _nome, qtd_req, _qtd_user, _qualidade in ingredientes:
            await self._consumir_ingrediente(interaction.user.id, ing_id, qtd_req)

        await self.bot.db.execute(
            """
            INSERT INTO inventario (user_id, nome, tipo, valor, efeito)
            VALUES (?, ?, 'Poção', 0, ?)
            """,
            (interaction.user.id, nome, efeito),
        )
        tox_aplicada = await self._ajustar_toxicidade(interaction.user.id, tox_total)
        await self.bot.db.commit()

        await interaction.response.send_message(
            (
                f"🧪 Você criou **{nome}**!\n"
                f"Efeito: {efeito}\n"
                f"Qualidade média: {media_qualidade} | Toxicidade +{tox_aplicada}.{colateral}"
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Alchemy(bot))
