import discord
import random
import asyncio
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional

TABELA_PRECOS = {"Comum": 50, "Incomum": 200, "Raro": 600, "Muito Raro": 1500, "Lendário": 4000}

# --- UI COMPONENTES ---

class BotaoConfirmarCompra(ui.Button):
    def __init__(self, dados, view):
        super().__init__(style=discord.ButtonStyle.success, label=f"Comprar ({dados['preco']}G)", emoji="✅", row=2)
        self.dados = dados
        self.view_pai = view

    async def callback(self, i: discord.Interaction):
        db = i.client.db
        
        async with db.execute("SELECT ouro FROM personagens WHERE user_id=?", (i.user.id,)) as c:
            row = await c.fetchone()
        if not row: return await i.response.send_message("❌ Sem ficha.", ephemeral=True)
        
        ouro = row[0]
        # Checa estoque
        async with db.execute("SELECT estoque FROM loja_itens WHERE id=?", (self.dados['id'],)) as c:
            stk = await c.fetchone()
            if not stk or stk[0] <= 0: return await i.response.send_message("❌ Esgotou!", ephemeral=True)

        if ouro < self.dados['preco']:
            return await i.response.send_message(f"💸 Falta ouro! Tens {ouro}G.", ephemeral=True)

        # Transação
        await db.execute("UPDATE personagens SET ouro = ouro - ? WHERE user_id=?", (self.dados['preco'], i.user.id))
        await db.execute("UPDATE loja_itens SET estoque = estoque - 1 WHERE id=?", (self.dados['id'],))
        await db.execute("INSERT INTO inventario (user_id, nome, tipo, valor, efeito) VALUES (?,?,?,?,?)",
                         (i.user.id, self.dados['nome'], self.dados['tipo'], self.dados['preco'], self.dados['efeito']))
        await db.commit()

        await i.response.send_message(f"✅ Comprou **{self.dados['nome']}**!", ephemeral=True)
        await self.view_pai.atualizar_comprar(i)

class BotaoVoltar(ui.Button):
    def __init__(self, view):
        super().__init__(style=discord.ButtonStyle.secondary, label="Voltar", emoji="↩️", row=2)
        self.view = view
    async def callback(self, i): await self.view.atualizar_comprar(i)

class SelectComprar(ui.Select):
    def __init__(self, itens, view):
        self.view_pai = view
        opts = []
        for id_item, nome, tipo, preco, estoque, efeito, preco_base in itens:
            self.view_pai.cache[str(id_item)] = {
                "id": id_item,
                "nome": nome,
                "tipo": tipo,
                "preco": preco,
                "estoque": estoque,
                "efeito": efeito,
                "preco_base": preco_base,
            }
            lbl = f"{nome} | 💰{preco}G" if estoque > 0 else f"{nome} (ESGOTADO)"
            emj = "🏷️" if estoque > 0 else "🔒"
            opts.append(discord.SelectOption(label=lbl[:100], value=str(id_item), description=tipo[:100], emoji=emj))
        super().__init__(placeholder="🔍 Ver detalhes...", options=opts, row=0)

    async def callback(self, i):
        d = self.view_pai.cache.get(self.values[0])
        if not d or d['estoque'] <= 0: return await i.response.send_message("🚫 Indisponível.", ephemeral=True)
        await self.view_pai.mostrar_detalhes(i, d)

class SelectVender(ui.Select):
    def __init__(self, inv):
        self.mapa = {}
        opts = []
        for id_inv, nome, tipo, valor in inv[:25]:
            venda = int(valor * 0.7)
            self.mapa[str(id_inv)] = {"nome": nome, "val": venda}
            opts.append(discord.SelectOption(label=f"{nome} | +{venda}G", value=str(id_inv), emoji="📤"))
        super().__init__(placeholder="💰 Vender item...", options=opts, row=0)

    async def callback(self, i):
        d = self.mapa.get(self.values[0])
        db = i.client.db
        await db.execute("DELETE FROM inventario WHERE id=?", (self.values[0],))
        await db.execute("UPDATE personagens SET ouro = ouro + ? WHERE user_id=?", (d['val'], i.user.id))
        # Retorna ao estoque
        res = await db.execute("UPDATE loja_itens SET estoque = estoque + 1 WHERE nome=?", (d['nome'],))
        await db.commit()
        msg = f"🤝 Vendeu **{d['nome']}** por {d['val']}G."
        if res.rowcount > 0: msg += "\n📦 Item voltou ao estoque!"
        await i.response.send_message(msg, ephemeral=True)
        await self.view.atualizar_vender(i)

# --- VIEW PRINCIPAL ---

class LojaView(ui.View):
    def __init__(self, db, uid, rep_multiplier: float, economy_mods: dict[str, float]):
        super().__init__(timeout=300)
        self.db = db
        self.uid = uid
        self.rep_multiplier = rep_multiplier
        self.economy_mods = economy_mods
        self.cache = {}

    def _categoria_economia(self, tipo: str | None) -> str | None:
        if not tipo:
            return None
        tipo_lower = tipo.lower()
        if "ingrediente" in tipo_lower and "monstro" in tipo_lower:
            return "Ingredientes de Monstro"
        if "comida" in tipo_lower or "alimento" in tipo_lower:
            return "Comida"
        return None

    def _preco_dinamico(self, preco_base: int, tipo: str | None) -> int:
        categoria = self._categoria_economia(tipo)
        economia = self.economy_mods.get(categoria, 1.0) if categoria else 1.0
        preco = int(preco_base * self.rep_multiplier * economia)
        return max(1, preco)

    async def check(self, i):
        if i.user.id != self.uid:
            await i.response.send_message("⛔ Use `/loja`.", ephemeral=True)
            return False
        return True

    @ui.button(label="Comprar", style=discord.ButtonStyle.primary, emoji="🛒", row=1)
    async def b_buy(self, i, b): 
        if await self.check(i): await self.atualizar_comprar(i)

    @ui.button(label="Vender", style=discord.ButtonStyle.success, emoji="💰", row=1)
    async def b_sell(self, i, b): 
        if await self.check(i): await self.atualizar_vender(i)

    @ui.button(label="Sair", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def b_exit(self, i, b): 
        if await self.check(i): await i.message.delete(); self.stop()

    def limpar_dinamico(self):
        keep = [x for x in self.children if getattr(x, 'row', 0) == 1]
        self.clear_items()
        for x in keep: self.add_item(x)

    async def mostrar_detalhes(self, i, d):
        self.limpar_dinamico()
        emb = discord.Embed(title=f"🔎 {d['nome']}", color=0x3498db)
        emb.description = f"**{d['tipo']}**\n\n📜 {d['efeito']}"
        emb.add_field(name="Preço", value=f"{d['preco']}G")
        if d.get("preco_base") is not None and d["preco_base"] != d["preco"]:
            emb.add_field(name="Preço base", value=f"{d['preco_base']}G")
        emb.add_field(name="Estoque", value=str(d['estoque']))
        self.add_item(BotaoConfirmarCompra(d, self))
        self.add_item(BotaoVoltar(self))
        await i.response.edit_message(embed=emb, view=self)

    async def atualizar_comprar(self, i):
        self.limpar_dinamico()
        self.cache = {}

        async def fetch_itens():
            # ORDER BY id DESC para novos itens aparecerem primeiro
            async with self.db.execute("SELECT id, nome, tipo, preco, estoque, efeito FROM loja_itens ORDER BY id DESC") as c:
                return await c.fetchall()

        async def fetch_ouro():
            async with self.db.execute("SELECT ouro FROM personagens WHERE user_id=?", (self.uid,)) as c:
                return (await c.fetchone() or [0])[0]

        itens, ouro = await asyncio.gather(fetch_itens(), fetch_ouro())

        itens_ajustados = []
        for id_item, nome, tipo, preco, estoque, efeito in itens:
            preco_final = self._preco_dinamico(preco, tipo)
            itens_ajustados.append((id_item, nome, tipo, preco_final, estoque, efeito, preco))
        
        emb = discord.Embed(title="🛒 Loja", description=f"Saldo: **{ouro}G**", color=0xD4AF37)
        if itens_ajustados: self.add_item(SelectComprar(itens_ajustados[:25], self))
        else: emb.description += "\n🚫 Vazia."
        
        if i.response.is_done(): await i.edit_original_response(embed=emb, view=self)
        else: await i.response.edit_message(embed=emb, view=self)

    async def atualizar_vender(self, i):
        self.limpar_dinamico()

        async def fetch_inv():
            async with self.db.execute("SELECT id, nome, tipo, valor FROM inventario WHERE user_id=?", (self.uid,)) as c:
                return await c.fetchall()

        async def fetch_ouro():
            async with self.db.execute("SELECT ouro FROM personagens WHERE user_id=?", (self.uid,)) as c:
                return (await c.fetchone() or [0])[0]

        inv, ouro = await asyncio.gather(fetch_inv(), fetch_ouro())
        
        emb = discord.Embed(title="💰 Venda", description=f"Saldo: **{ouro}G** (Pagamos 70%)", color=0x2ecc71)
        if inv: self.add_item(SelectVender(inv))
        else: emb.description += "\n🎒 Vazio."
        
        if i.response.is_done(): await i.edit_original_response(embed=emb, view=self)
        else: await i.response.edit_message(embed=emb, view=self)

# --- COG ---

class Shop(commands.Cog):
    def __init__(self, bot): self.bot = bot
    def is_mestre(i: discord.Interaction): return i.user.guild_permissions.administrator

    async def _calcular_multiplicadores(self, user_id: int, localizacao_id: int | None) -> tuple[float, dict[str, float]]:
        async def fetch_reputacao():
            async with self.bot.db.execute(
                "SELECT COALESCE(SUM(reputacao), 0) FROM reputacoes WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                return (await cursor.fetchone() or [0])[0]

        async def fetch_economy():
            if not localizacao_id:
                return []
            async with self.bot.db.execute(
                "SELECT categoria, modificador FROM economia_regional WHERE localizacao_id = ?",
                (localizacao_id,),
            ) as cursor:
                return await cursor.fetchall()

        reputacao_total, economy_rows = await asyncio.gather(fetch_reputacao(), fetch_economy())

        bonus = max(-0.2, min(0.2, reputacao_total / 100))
        rep_multiplier = 1 - bonus

        economy_mods = {categoria: modificador for categoria, modificador in economy_rows}
        return rep_multiplier, economy_mods

    async def ac_item(self, i, current: str):
        async with self.bot.db.execute("SELECT nome FROM loja_itens WHERE nome LIKE ? LIMIT 25", (f'%{current}%',)) as c:
            return [app_commands.Choice(name=r[0], value=r[0]) for r in await c.fetchall()]

    @app_commands.command(name="loja", description="🏪 Abre a loja")
    async def loja(self, i: discord.Interaction):
        async with self.bot.db.execute(
            "SELECT id, localizacao_id FROM personagens WHERE user_id=?",
            (i.user.id,),
        ) as c:
            row = await c.fetchone()
            if not row:
                return await i.response.send_message("❌ Crie ficha.", ephemeral=True)
        _, localizacao_id = row
        rep_multiplier, economy_mods = await self._calcular_multiplicadores(i.user.id, localizacao_id)
        view = LojaView(self.bot.db, i.user.id, rep_multiplier, economy_mods)
        await view.atualizar_comprar(i) # Inicia visualização
        # Nota: O método atualizar_comprar usa edit, mas a primeira precisa ser send.
        # Ajuste no View: Se response.is_done() usa edit, senao usa send_message (já implementado acima).
        # Mas para garantir o fluxo, vamos mandar uma dummy e deixar a view editar.
        emb = discord.Embed(title="Carregando Loja...", color=0xD4AF37)
        await i.response.send_message(embed=emb, view=view)
        await view.atualizar_comprar(i)

    @app_commands.command(name="loja_adicionar", description="🔒 (Mestre) Adiciona item (Efeito Vazio = IA)")
    @app_commands.check(is_mestre)
    async def add(self, i: discord.Interaction, nome: str, tipo: str, preco: int, estoque: int, efeito: Optional[str]=None):
        if not efeito:
            await i.response.defer()
            ai = self.bot.get_cog("AIHandler")
            efeito = await ai.gerar_descricao_item(nome, tipo) if ai else "Sem desc."
            await self.bot.db.execute("INSERT INTO loja_itens (nome,tipo,preco,estoque,efeito) VALUES (?,?,?,?,?)", (nome,tipo,preco,estoque,efeito))
            await self.bot.db.commit()
            await i.followup.send(f"🤖 **IA Forjou:** {nome}\n📜 {efeito}")
        else:
            await self.bot.db.execute("INSERT INTO loja_itens (nome,tipo,preco,estoque,efeito) VALUES (?,?,?,?,?)", (nome,tipo,preco,estoque,efeito))
            await self.bot.db.commit()
            await i.response.send_message(f"✅ {nome} adicionado.", ephemeral=True)

    @app_commands.command(name="loja_gerar", description="🔒 (Mestre) Geração IA (1% Mítico)")
    @app_commands.choices(raridade=[
        app_commands.Choice(name="Comum (50G)", value="Comum"),
        app_commands.Choice(name="Lendário (4000G)", value="Lendário")
    ])
    @app_commands.check(is_mestre)
    async def gen(self, i: discord.Interaction, raridade: str, tipo: Optional[str]=None):
        await i.response.defer()
        pb = TABELA_PRECOS.get(raridade, 50)
        mitico = False
        if raridade=="Lendário" and random.random() <= 0.01:
            raridade = "Mítico (Ancestral)"
            pb *= 2
            mitico = True
        
        ai = self.bot.get_cog("AIHandler")
        if not ai: return await i.followup.send("❌ IA Off.")
        
        item = await ai.gerar_item_aleatorio(f"{raridade} {tipo or ''}")
        if not item: return await i.followup.send("❌ Falha IA.")

        await self.bot.db.execute("INSERT INTO loja_itens (nome,tipo,preco,estoque,efeito) VALUES (?,?,?,?,?)", 
                                  (item['nome'], item['tipo'], pb, 1 if mitico else 5, item['efeito']))
        await self.bot.db.commit()
        
        cor = 0xFFD700 if mitico else 0x3498db
        emb = discord.Embed(title="🌟 ITEM MÍTICO!" if mitico else "🔨 Item Forjado", color=cor)
        emb.add_field(name="Nome", value=item['nome'])
        emb.description = item['efeito']
        await i.followup.send(embed=emb)

    @app_commands.command(name="loja_estoque")
    @app_commands.autocomplete(nome_item=ac_item)
    @app_commands.check(is_mestre)
    async def stk(self, i: discord.Interaction, nome_item: str, qtd: int):
        c = await self.bot.db.execute("UPDATE loja_itens SET estoque=? WHERE nome=?", (qtd, nome_item))
        await self.bot.db.commit()
        await i.response.send_message(f"✅ Estoque atualizado." if c.rowcount else "❌ Item não existe.", ephemeral=True)

    @app_commands.command(name="loja_remover")
    @app_commands.autocomplete(nome_item=ac_item)
    @app_commands.check(is_mestre)
    async def rem(self, i: discord.Interaction, nome_item: str):
        c = await self.bot.db.execute("DELETE FROM loja_itens WHERE nome LIKE ?", (f"%{nome_item}%",))
        await self.bot.db.commit()
        await i.response.send_message(f"🗑️ Removido." if c.rowcount else "❌ Não achei.", ephemeral=True)

async def setup(bot): await bot.add_cog(Shop(bot))
