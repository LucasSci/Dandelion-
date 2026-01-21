import discord
import io
import json
from typing import Optional
from discord.ext import commands
from discord import app_commands
from data_cache import get_world_location_names
from ui.modals import CriarFichaModal
from ui.sheet_view import FichaView, construir_embed_ficha
from data.repositories import CharacterRepository, SkillRepository
LOCALIZACOES_ARMADURA = {
    "Cabeça": "cabeca",
    "Torso": "torso",
    "Braços": "bracos",
    "Pernas": "pernas",
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
        self.character_repo = CharacterRepository(bot.db)
        self.skill_repo = SkillRepository(bot.db)

    # --- AUTOCOMPLETES ---
    async def personagens_disponiveis_autocomplete(self, interaction: discord.Interaction, current: str):
        rows = await self.character_repo.list_available_names(current)
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def meus_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        rows = await self.character_repo.list_user_names(interaction.user.id, current)
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def todos_personagens_autocomplete(self, interaction: discord.Interaction, current: str):
        rows = await self.character_repo.list_all_names(current)
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def localizacao_autocomplete(self, interaction: discord.Interaction, current: str):
        nomes = await get_world_location_names(self.bot.db)
        termo = current.strip().lower()
        if termo:
            nomes = [nome for nome in nomes if termo in nome.lower()]
        return [app_commands.Choice(name=nome, value=nome) for nome in nomes[:25]]
        rows = await self.character_repo.list_location_names(current)
        return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

    async def _buscar_personagem(self, user_id: int):
        return await self.character_repo.fetch_character_summary_by_user(user_id)

    def _permitir_alvo(self, interaction: discord.Interaction, usuario: Optional[discord.Member]) -> bool:
        return usuario is None or usuario.id == interaction.user.id or is_mestre(interaction)

    # --- COMANDOS DE MESTRE (XP, NÍVEL E OURO) ---

    @app_commands.command(name="mestre_add_xp", description="🔒 (Mestre) Dá XP ao jogador e processa Level Up")
    @app_commands.check(is_mestre)
    async def mestre_add_xp(
        self,
        interaction: discord.Interaction,
        xp: int,
        usuario: Optional[discord.Member] = None,
    ):
        await interaction.response.defer()

        target = usuario or interaction.user
        db = self.bot.db
        async with db.execute(
            "SELECT nivel, xp_atual, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?",
            (target.id,),
        ) as cursor:
            dados = await cursor.fetchone()
        
        dados = await self.character_repo.fetch_progress_by_user(usuario.id)
        
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
        """, (nivel, xp_atual, hp_max, hp_atual, ataque, target.id))
        await db.commit()
        await self.character_repo.update_progress(usuario.id, nivel, xp_atual, hp_max, hp_atual, ataque)

        msg = f"✨ **{target.display_name}** ganhou {xp} XP!"
        if niveis_subidos > 0:
            msg += f"\n🎉 **LEVEL UP!** Subiu {niveis_subidos} nível(is)!\nAgora Nível **{nivel}** (HP: {hp_max}, Atk: {ataque})"
        else:
            msg += f"\nXP Atual: {xp_atual}/{nivel*1000}"

        await interaction.followup.send(msg)

    @app_commands.command(name="mestre_levelup", description="🔒 (Mestre) Força a subida de 1 nível")
    @app_commands.check(is_mestre)
    async def mestre_levelup(
        self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None
    ):
        target = usuario or interaction.user
        db = self.bot.db
        async with db.execute(
            "SELECT nivel, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?",
            (target.id,),
        ) as cursor:
            dados = await cursor.fetchone()
    async def mestre_levelup(self, interaction: discord.Interaction, usuario: discord.Member):
        dados = await self.character_repo.fetch_level_stats_by_user(usuario.id)
        
        if not dados: return await interaction.response.send_message("❌ Sem ficha.", ephemeral=True)
        
        nivel, hp_max, hp_atual, ataque = dados
        if hp_atual is None: hp_atual = hp_max

        novo_nivel = nivel + 1
        novo_hp = hp_max + 5
        novo_hp_atual = hp_atual + 5
        novo_ataque = ataque + 1

        await db.execute("""
            UPDATE personagens SET nivel=?, hp_max=?, hp_atual=?, ataque=? WHERE user_id=?
        """, (novo_nivel, novo_hp, novo_hp_atual, novo_ataque, target.id))
        await db.commit()
        await self.character_repo.update_level_stats(usuario.id, novo_nivel, novo_hp, novo_hp_atual, novo_ataque)

        await interaction.response.send_message(
            f"🆙 **{target.display_name}** foi promovido para o Nível **{novo_nivel}**!\n(+5 HP, +1 Atk)"
        )

    @app_commands.command(name="mestre_leveldown", description="🔒 (Mestre) Remove 1 nível (corrige erro)")
    @app_commands.check(is_mestre)
    async def mestre_leveldown(
        self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None
    ):
        target = usuario or interaction.user
        db = self.bot.db
        async with db.execute(
            "SELECT nivel, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?",
            (target.id,),
        ) as cursor:
            dados = await cursor.fetchone()
    async def mestre_leveldown(self, interaction: discord.Interaction, usuario: discord.Member):
        dados = await self.character_repo.fetch_level_stats_by_user(usuario.id)
        
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
        """, (novo_nivel, novo_hp, novo_hp_atual, novo_ataque, target.id))
        await db.commit()
        await self.character_repo.update_level_stats(usuario.id, novo_nivel, novo_hp, novo_hp_atual, novo_ataque)

        await interaction.response.send_message(
            f"🔻 **{target.display_name}** retornou para o Nível **{novo_nivel}**.\nStatus revertidos."
        )

    # --- NOVO COMANDO: GERENCIAR OURO ---
    @app_commands.command(name="mestre_ouro", description="🔒 (Mestre) Adiciona ou remove ouro (Use negativo para remover)")
    @app_commands.check(is_mestre)
    async def mestre_ouro(
        self,
        interaction: discord.Interaction,
        quantidade: int,
        usuario: Optional[discord.Member] = None,
    ):
        target = usuario or interaction.user
        db = self.bot.db
        async with db.execute(
            "SELECT ouro FROM personagens WHERE user_id = ?", (target.id,)
        ) as cursor:
            dados = await cursor.fetchone()

        if not dados:
    async def mestre_ouro(self, interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
        ouro_atual = await self.character_repo.fetch_gold_by_user(usuario.id)
        if ouro_atual is None:
            return await interaction.response.send_message("❌ Esse usuário não tem ficha.", ephemeral=True)
        # Garante que o ouro não fique negativo
        novo_ouro = max(0, ouro_atual + quantidade)

        await db.execute(
            "UPDATE personagens SET ouro = ? WHERE user_id = ?", (novo_ouro, target.id)
        )
        await db.commit()
        await self.character_repo.update_gold_by_user(usuario.id, novo_ouro)

        if quantidade > 0:
            await interaction.response.send_message(
                f"💰 **{target.display_name}** recebeu **{quantidade}** moedas de ouro!\n(Total: {novo_ouro})"
            )
        else:
            perda = abs(quantidade)
            await interaction.response.send_message(
                f"💸 **{target.display_name}** perdeu **{perda}** moedas de ouro.\n(Total: {novo_ouro})"
            )

    # --- LOCALIZACAO / MUNDO ---
    @app_commands.command(name="localizacao", description="Mostra a localização atual do personagem")
    async def localizacao(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        row = await self.character_repo.fetch_location_by_user(target.id)

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

        local_id = await self.character_repo.fetch_location_id(destino)
        if not local_id:
            return await interaction.response.send_message("❌ Localização não encontrada.", ephemeral=True)
        rowcount = await self.character_repo.update_location(target.id, local_id)
        if rowcount == 0:
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
        await self.character_repo.upsert_attribute(personagem_id, nome, valor)

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
        atributos = await self.character_repo.list_attributes(personagem_id)

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
        await self.character_repo.upsert_armor(personagem_id, localizacao, sp)

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
        armadura = await self.character_repo.fetch_armor(personagem_id, localizacao)
        if armadura:
            armadura_id = armadura[0]
        else:
            armadura_id = await self.character_repo.create_armor(personagem_id, localizacao)

        await self.character_repo.upsert_armor_modifier(armadura_id, tipo_dano, multiplicador)

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

        armadura = await self.character_repo.fetch_armor(personagem_id, localizacao)

        sp_base = armadura[1] if armadura else 0
        reliability = armadura[2] if armadura and armadura[2] is not None else 100
        reliability = max(0, min(100, reliability))
        sp_atual = max(0, int(sp_base * (reliability / 100))) if sp_base > 0 else 0
        multiplicador = 1.0
        if tipo_dano and armadura:
            mod_value = await self.character_repo.fetch_armor_modifier(armadura[0], tipo_dano)
            if mod_value is not None:
                multiplicador = mod_value

        dano_reduzido = max(0, dano - sp_atual)
        dano_final = max(0, int(round(dano_reduzido * multiplicador)))
        novo_hp = max(0, hp_atual - dano_final)

        nova_reliability = reliability
        novo_sp_atual = sp_atual
        if armadura and sp_base > 0 and dano > 0:
            reducao_sp = max(1, dano // 5)
            novo_sp_atual = max(0, sp_atual - reducao_sp)
            nova_reliability = max(0, min(100, int(round((novo_sp_atual / sp_base) * 100))))
            await self.character_repo.update_armor_reliability(armadura[0], nova_reliability)

        await self.character_repo.update_hp(personagem_id, novo_hp)

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

        personagem = await self.character_repo.fetch_export_character(target.id)

        if not personagem:
            return await interaction.response.send_message(
                "❌ Nenhuma ficha encontrada.", ephemeral=True
            )

        personagem_id = personagem[0]
        habilidades = await self.skill_repo.list_skill_export(personagem_id)

        atributos = await self.character_repo.list_attributes(personagem_id)

        armaduras = await self.character_repo.list_armors(personagem_id, ["cabeca", "torso", "pernas"])

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

        armaduras = await self.character_repo.list_armors(personagem_id)

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
        if await self.character_repo.user_has_character(interaction.user.id):
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
        if await self.character_repo.user_has_character(interaction.user.id):
            return await interaction.response.send_message("❌ Você já tem um personagem!", ephemeral=True)

        rowcount = await self.character_repo.assign_character(interaction.user.id, nome_personagem)
        if rowcount > 0:
            await interaction.response.send_message(f"⚔️ Agora você é **{nome_personagem}**! Use `/ficha` para ver o painel.")
        else:
            await interaction.response.send_message("❌ Erro ao assumir ficha.", ephemeral=True)

    @app_commands.command(name="devolver_ficha", description="Devolve ficha ao Pool")
    @app_commands.autocomplete(nome_personagem=meus_personagens_autocomplete)
    async def devolver_ficha(self, interaction: discord.Interaction, nome_personagem: str):
        rowcount = await self.character_repo.release_character(interaction.user.id, nome_personagem)
        if rowcount > 0:
            await interaction.response.send_message(f"👋 Você devolveu **{nome_personagem}** ao Pool.")
        else:
            await interaction.response.send_message("❌ Personagem não encontrado.", ephemeral=True)

    @app_commands.command(name="mestre_vincular", description="🔒 (Mestre) Transfere ficha")
    @app_commands.check(is_mestre)
    @app_commands.autocomplete(nome_personagem=todos_personagens_autocomplete)
    async def mestre_vincular(
        self,
        interaction: discord.Interaction,
        nome_personagem: str,
        usuario: Optional[discord.Member] = None,
    ):
        target = usuario or interaction.user
        await self.bot.db.execute(
            "UPDATE personagens SET user_id = NULL WHERE user_id = ?", (target.id,)
        )
        cursor = await self.bot.db.execute(
            "UPDATE personagens SET user_id = ? WHERE nome = ?",
            (target.id, nome_personagem),
        )
        await self.bot.db.commit()
        if cursor.rowcount > 0:
            await interaction.response.send_message(
                f"✅ **{nome_personagem}** vinculado a {target.mention}."
            )
    async def mestre_vincular(self, interaction: discord.Interaction, nome_personagem: str, usuario: discord.Member):
        await self.character_repo.clear_user_character(usuario.id)
        rowcount = await self.character_repo.assign_character_to_user(usuario.id, nome_personagem)
        if rowcount > 0:
            await interaction.response.send_message(f"✅ **{nome_personagem}** vinculado a {usuario.mention}.")
        else:
            await interaction.response.send_message("❌ Erro ao vincular.", ephemeral=True)

    # --- COMANDO FICHA (O PAINEL INTERATIVO) ---
    @app_commands.command(name="ficha", description="Abre o painel interativo do personagem")
    async def ficha(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user

        char_id = await self.character_repo.fetch_character_id_by_user(target.id)
        if not char_id:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        embed = await construir_embed_ficha(self.bot.db, char_id, target.id)
        if not embed:
            return await interaction.response.send_message("❌ Nenhuma ficha encontrada.", ephemeral=True)

        view = FichaView(self.bot, personagem_id=char_id, user_id_dono=target.id)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="listar_fichas", description="Lista todas as fichas")
    async def listar_fichas(self, interaction: discord.Interaction):
        # Otimização: LIMIT 20 para evitar carregar todas as fichas desnecessariamente
        rows = await self.character_repo.list_characters(limit=20)
        if not rows:
            return await interaction.response.send_message("📭 Nenhuma ficha.", ephemeral=True)
        txt = "\n".join([f"• {r[0]} ({'Ocupado' if r[1] else 'Livre'})" for r in rows])
        await interaction.response.send_message(f"**Fichas:**\n{txt}")

async def setup(bot):
    await bot.add_cog(Characters(bot))
