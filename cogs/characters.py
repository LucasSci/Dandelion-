import aiosqlite
import discord
import io
import json
import math
from typing import Optional
from discord.ext import commands
from discord import app_commands
from ui.modals import CriarFichaModal
from ui.sheet_view import FichaView, construir_embed_ficha
from enums import BodyPart

DB_NAME = "bestiario.db"
LOCALIZACOES_ARMADURA = {
    "Cabeça": BodyPart.HEAD.value,
    "Torso": BodyPart.TORSO.value,
    "Braços": BodyPart.ARMS.value,
    "Pernas": BodyPart.LEGS.value,
}
LOCALIZACOES_ARMADURA_CHOICES = [
    app_commands.Choice(name=nome, value=valor)
    for nome, valor in LOCALIZACOES_ARMADURA.items()
]

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

    async def _buscar_personagem(self, user_id: int):
        async with self.bot.db.execute(
            "SELECT id, nome, hp_atual, hp_max FROM personagens WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()

    def _permitir_alvo(self, interaction: discord.Interaction, usuario: Optional[discord.Member]) -> bool:
        return usuario is None or usuario.id == interaction.user.id or is_mestre(interaction)

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

        xp_total = xp_atual + xp + (nivel - 1) * nivel * 500
        xp_total = max(0, xp_total)
        xp_total_unidades = xp_total // 1000
        novo_nivel = max(1, (1 + math.isqrt(1 + 8 * xp_total_unidades)) // 2)
        niveis_subidos = max(0, novo_nivel - nivel)
        nivel = novo_nivel
        xp_atual = max(0, xp_total - (nivel - 1) * nivel * 500)

        if niveis_subidos:
            hp_max += 5 * niveis_subidos
            hp_atual += 5 * niveis_subidos
            ataque += 1 * niveis_subidos
        
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

    # --- ATRIBUTOS / PERÍCIAS ---
    @app_commands.command(name="atributo_definir", description="Define o valor de um atributo.")
    async def atributo_definir(
        self,
        interaction: discord.Interaction,
        nome: str,
        valor: int,
        usuario: Optional[discord.Member] = None
    ):
        if not self._permitir_alvo(interaction, usuario):
            return await interaction.response.send_message("❌ Apenas o Mestre pode ajustar outros jogadores.", ephemeral=True)

        target = usuario or interaction.user
        personagem = await self._buscar_personagem(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, _, _ = personagem
        await self.bot.db.execute(
            """
            INSERT INTO atributos_personagem (personagem_id, nome, valor)
            VALUES (?, ?, ?)
            ON CONFLICT(personagem_id, nome) DO UPDATE SET valor = excluded.valor
            """,
            (personagem_id, nome.strip(), valor)
        )
        await self.bot.db.commit()

        await interaction.response.send_message(
            f"✅ Atributo **{nome}** atualizado para **{valor}** em {personagem_nome}."
        )

    @app_commands.command(name="atributo_listar", description="Lista os atributos cadastrados.")
    async def atributo_listar(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None
    ):
        if not self._permitir_alvo(interaction, usuario):
            return await interaction.response.send_message("❌ Apenas o Mestre pode ver atributos de outros jogadores.", ephemeral=True)

        target = usuario or interaction.user
        personagem = await self._buscar_personagem(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, _, _ = personagem
        async with self.bot.db.execute(
            "SELECT nome, valor FROM atributos_personagem WHERE personagem_id = ? ORDER BY nome",
            (personagem_id,)
        ) as cursor:
            atributos = await cursor.fetchall()

        if not atributos:
            return await interaction.response.send_message("📭 Nenhum atributo cadastrado.")

        linhas = "\n".join([f"• **{nome}**: {valor}" for nome, valor in atributos])
        await interaction.response.send_message(f"📋 Atributos de **{personagem_nome}**:\n{linhas}")

    # --- ARMADURA / DANO ---
    @app_commands.command(name="armadura_definir", description="Define o SP da armadura por localização.")
    @app_commands.choices(localizacao=LOCALIZACOES_ARMADURA_CHOICES)
    async def armadura_definir(
        self,
        interaction: discord.Interaction,
        localizacao: str,
        sp: int,
        usuario: Optional[discord.Member] = None
    ):
        if not self._permitir_alvo(interaction, usuario):
            return await interaction.response.send_message("❌ Apenas o Mestre pode ajustar outros jogadores.", ephemeral=True)

        target = usuario or interaction.user
        personagem = await self._buscar_personagem(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, _, _ = personagem
        await self.bot.db.execute(
            """
            INSERT INTO armaduras_personagem (personagem_id, localizacao, sp, reliability)
            VALUES (?, ?, ?, 100)
            ON CONFLICT(personagem_id, localizacao) DO UPDATE SET sp = excluded.sp
            """,
            (personagem_id, localizacao, sp)
        )
        await self.bot.db.commit()

        await interaction.response.send_message(
            f"🛡️ SP de **{personagem_nome}** em **{localizacao}** definido para **{sp}**."
        )

    @app_commands.command(name="armadura_modificador", description="Define modificador de tipo de dano por localização.")
    @app_commands.choices(localizacao=LOCALIZACOES_ARMADURA_CHOICES)
    async def armadura_modificador(
        self,
        interaction: discord.Interaction,
        localizacao: str,
        tipo_dano: str,
        multiplicador: float,
        usuario: Optional[discord.Member] = None
    ):
        if not self._permitir_alvo(interaction, usuario):
            return await interaction.response.send_message("❌ Apenas o Mestre pode ajustar outros jogadores.", ephemeral=True)

        target = usuario or interaction.user
        personagem = await self._buscar_personagem(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, _, _ = personagem
        async with self.bot.db.execute(
            "SELECT id FROM armaduras_personagem WHERE personagem_id = ? AND localizacao = ?",
            (personagem_id, localizacao)
        ) as cursor:
            armadura = await cursor.fetchone()

        if armadura:
            armadura_id = armadura[0]
        else:
            cursor = await self.bot.db.execute(
                """
                INSERT INTO armaduras_personagem (personagem_id, localizacao, sp, reliability)
                VALUES (?, ?, 0, 100)
                """,
                (personagem_id, localizacao)
            )
            armadura_id = cursor.lastrowid

        await self.bot.db.execute(
            """
            INSERT INTO armadura_modificadores (armadura_id, tipo_dano, multiplicador)
            VALUES (?, ?, ?)
            ON CONFLICT(armadura_id, tipo_dano) DO UPDATE SET multiplicador = excluded.multiplicador
            """,
            (armadura_id, tipo_dano.strip().lower(), multiplicador)
        )
        await self.bot.db.commit()

        await interaction.response.send_message(
            f"🧪 Modificador **{multiplicador}x** para **{tipo_dano}** em **{localizacao}** de {personagem_nome}."
        )

    @app_commands.command(name="receber_dano", description="Aplica dano com SP e modificadores de armadura.")
    @app_commands.choices(localizacao=LOCALIZACOES_ARMADURA_CHOICES)
    async def receber_dano(
        self,
        interaction: discord.Interaction,
        dano: int,
        localizacao: str,
        tipo_dano: Optional[str] = None,
        usuario: Optional[discord.Member] = None
    ):
        if dano < 0:
            return await interaction.response.send_message("❌ O dano deve ser positivo.", ephemeral=True)
        if not self._permitir_alvo(interaction, usuario):
            return await interaction.response.send_message("❌ Apenas o Mestre pode aplicar dano em outros jogadores.", ephemeral=True)

        target = usuario or interaction.user
        personagem = await self._buscar_personagem(target.id)
        if not personagem:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        personagem_id, personagem_nome, hp_atual, hp_max = personagem
        if hp_atual is None:
            hp_atual = hp_max

        async with self.bot.db.execute(
            "SELECT id, sp, reliability FROM armaduras_personagem WHERE personagem_id = ? AND localizacao = ?",
            (personagem_id, localizacao)
        ) as cursor:
            armadura = await cursor.fetchone()

        sp_base = armadura[1] if armadura else 0
        reliability = armadura[2] if armadura and armadura[2] is not None else 100
        reliability = max(0, min(100, reliability))
        sp_atual = max(0, int(sp_base * (reliability / 100))) if sp_base > 0 else 0
        multiplicador = 1.0
        if tipo_dano and armadura:
            async with self.bot.db.execute(
                "SELECT multiplicador FROM armadura_modificadores WHERE armadura_id = ? AND tipo_dano = ?",
                (armadura[0], tipo_dano.strip().lower())
            ) as cursor:
                mod_row = await cursor.fetchone()
            if mod_row:
                multiplicador = mod_row[0]

        dano_reduzido = max(0, dano - sp_atual)
        dano_final = max(0, int(round(dano_reduzido * multiplicador)))
        novo_hp = max(0, hp_atual - dano_final)

        nova_reliability = reliability
        novo_sp_atual = sp_atual
        if armadura and sp_base > 0 and dano > 0:
            reducao_sp = max(1, dano // 5)
            novo_sp_atual = max(0, sp_atual - reducao_sp)
            nova_reliability = max(0, min(100, int(round((novo_sp_atual / sp_base) * 100))))
            await self.bot.db.execute(
                "UPDATE armaduras_personagem SET reliability = ? WHERE id = ?",
                (nova_reliability, armadura[0])
            )

        await self.bot.db.execute(
            "UPDATE personagens SET hp_atual = ? WHERE id = ?",
            (novo_hp, personagem_id)
        )
        await self.bot.db.commit()

        tipo_txt = f" ({tipo_dano})" if tipo_dano else ""
        resposta = (
            f"💥 **{personagem_nome}** recebeu **{dano}** de dano{tipo_txt} em **{localizacao}**.\n"
            f"🛡️ SP: {sp_atual} (Base {sp_base} | Rel {reliability}%) | 🔻 Dano após SP: {dano_reduzido}\n"
        )
        if armadura and sp_base > 0 and dano > 0:
            resposta += f"🧱 Integridade: {reliability}% → {nova_reliability}% (SP efetivo {sp_atual} → {novo_sp_atual})\n"
        if multiplicador != 1.0:
            resposta += f"🧪 Multiplicador: {multiplicador}x | Dano final: {dano_final}\n"
        else:
            resposta += f"✅ Dano final: {dano_final}\n"
        if armadura and sp_base > 0 and dano > 0:
            resposta += f"🛡️ Reliability: {reliability}% → {nova_reliability}%\n"
        resposta += f"❤️ HP: {hp_atual} → {novo_hp}"

        await interaction.response.send_message(resposta)

    @app_commands.command(name="ficha_exportar", description="📤 Exporta a ficha em JSON.")
    async def ficha_exportar(
        self, interaction: discord.Interaction, usuario: discord.Member = None
    ):
        target = usuario or interaction.user

        async with self.bot.db.execute(
            """
            SELECT id, nome, raca, classe, nivel, xp_atual, historia, imagem_url, ouro,
                   hp_max, hp_atual, mp_max, ataque, defesa, vigor_max, vigor_atual,
                   toxicidade_max, toxicidade_atual
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
            "SELECT nome, valor FROM atributos_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            atributos = await cursor.fetchall()

        async with self.bot.db.execute(
            """
            SELECT localizacao, sp, reliability
            FROM armaduras_personagem
            WHERE personagem_id = ? AND localizacao IN ('cabeca', 'torso', 'pernas')
            """,
            (personagem_id,),
        ) as cursor:
            armaduras = await cursor.fetchall()

        atributos_map = {nome: valor for nome, valor in atributos}
        armor_defaults = {
            "cabeca": {"sp": 0, "reliability": 100},
            "torso": {"sp": 0, "reliability": 100},
            "pernas": {"sp": 0, "reliability": 100},
        }
        for localizacao, sp, reliability in armaduras:
            armor_defaults[localizacao] = {
                "sp": sp or 0,
                "reliability": reliability if reliability is not None else 100,
            }

        async with self.bot.db.execute(
            "SELECT localizacao, sp, reliability FROM armaduras_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            armaduras = await cursor.fetchall()

        export_localizacoes = ["cabeca", "torso", "pernas"]
        armor_layers = {
            localizacao: {"sp": 0, "reliability": 100}
            for localizacao in export_localizacoes
        }
        for localizacao, sp, reliability in armaduras:
            if localizacao in armor_layers:
                armor_layers[localizacao] = {
                    "sp": sp or 0,
                    "reliability": reliability if reliability is not None else 100,
                }

        ficha = {
            "schema_version": "v1.0.0",
            "character_name": personagem[1],
            "core_stats": {
                "INT": atributos_map.get("INT", 1),
                "REF": atributos_map.get("REF", 1),
                "DEX": atributos_map.get("DEX", 1),
                "BODY": atributos_map.get("BODY", 1),
                "SPD": atributos_map.get("SPD", 1),
                "EMP": atributos_map.get("EMP", 1),
                "CRA": atributos_map.get("CRA", 1),
                "WILL": atributos_map.get("WILL", 1),
                "LUCK": atributos_map.get("LUCK", 1),
            },
            "derived_stats": {
                "Stun": 0,
                "Run": 0,
                "Leap": 0,
                "HP": personagem[9],
                "Stamina": personagem[14] if personagem[14] is not None else 0,
                "Vigor": personagem[15] if personagem[15] is not None else 0,
                "Recovery": 0,
            },
            "skills_tree": [
                {
                    "nome": h[0],
                    "stat_base": "INT",
                    "pontos_investidos": 0,
                    "modificadores": 0,
                }
                for h in habilidades
            ],
            "witcher_specifics": {
                "toxicity": {
                    "current": personagem[17] if personagem[17] is not None else 0,
                    "max": personagem[16] if personagem[16] is not None else 0,
                },
                "focus": 0,
            },
            "armor_layers": {**armor_layers},
            "atributos": {
                "hp_max": personagem[9],
                "hp_atual": personagem[10],
                "mp_max": personagem[11],
                "ataque": personagem[12],
                "defesa": personagem[13],
                "head": armor_defaults["cabeca"],
                "torso": armor_defaults["torso"],
                "legs": armor_defaults["pernas"],
            },
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
            SELECT p.id
            FROM personagens p
            WHERE p.user_id = ?
        """, (target.id,)) as cursor:
            res = await cursor.fetchone()
        
        if not res:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        char_id = res[0]

        embed = await construir_embed_ficha(self.bot.db, char_id, target.id)
        if not embed:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

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
