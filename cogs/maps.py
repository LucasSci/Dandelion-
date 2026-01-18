import discord
from discord.ext import commands
from discord import app_commands
import io
import math
import asyncio
from PIL import Image, ImageDraw, ImageFont

class Maps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Funções Auxiliares ---
    
    def calcular_distancia(self, x1, y1, x2, y2):
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def obter_tempo_viagem(self, distancia_pixels):
        # Regra da casa: 50 pixels = 1 dia de viagem a cavalo
        dias = int(distancia_pixels / 50)
        return max(1, dias) # Mínimo 1 dia

    async def gerar_imagem_mapa(self, p_x, p_y, p_nome, p_local_atual, quests_ativas=None):
        """
        Gera a imagem usando o mapa da região onde o jogador está.
        """
        # Mapeia o nome do local no DB para o nome do arquivo
        mapa_files = {
            "Novigrad": "assets/novigrad.jpg",
            "Velen": "assets/velen.jpg",
            "Skellige": "assets/skellige.jpg",
            "Kaer Morhen": "assets/kaer_morhen.jpg",
            "Deserto de Korath": "assets/korath.jpg",
            "Toussaint": "assets/toussaint.jpg"
        }
        
        arquivo_mapa = mapa_files.get(p_local_atual, "assets/world_map.jpg") # Fallback

        try:
            mapa = Image.open(arquivo_mapa).convert("RGBA")
            # Nota: Se os mapas regionais tiverem tamanhos diferentes, 
            # você talvez precise ajustar a escala das coordenadas X,Y.
            # Por simplicidade, tente gerar todos em 1024x1024.
            mapa = mapa.resize((1024, 1024)) 
        except:
            # Fallback se a imagem específica não existir
            mapa = Image.new('RGB', (1024, 1024), color=(210, 180, 140))

    # --- Autocompletes ---

    async def locais_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.db.execute("SELECT nome FROM locais_mundo WHERE nome LIKE ? LIMIT 25", (f'%{current}%',)) as c:
            return [app_commands.Choice(name=r[0], value=r[0]) for r in await c.fetchall()]

    # --- Comandos ---

    @app_commands.command(name="mapa", description="🗺️ Abre o mapa mundi, mostrando sua posição e missões.")
    async def ver_mapa(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # 1. Pega dados do Jogador
        async with self.bot.db.execute("SELECT nome, localizacao_atual, coord_x, coord_y FROM personagens WHERE user_id=?", (interaction.user.id,)) as c:
            p_data = await c.fetchone()
        
        if not p_data:
            return await interaction.followup.send("❌ Você precisa criar uma ficha primeiro (`/criar_ficha`).")
        
        p_nome, p_local, p_x, p_y = p_data

        # 2. Pega Quests Disponíveis (Status = Disponivel)
        async with self.bot.db.execute("SELECT titulo, coord_x, coord_y FROM quests WHERE status='Disponivel'") as c:
            quests = await c.fetchall()

        # 3. Gera a Imagem
        buffer = await self.gerar_imagem_mapa(p_x, p_y, p_local, quests)
        file = discord.File(buffer, filename="mapa_mundo.png")

        embed = discord.Embed(title=f"🗺️ Mapa de {p_nome}", color=0xDAA520)
        embed.description = f"📍 Local Atual: **{p_local}**\n📜 Missões Ativas no Mundo: **{len(quests)}**"
        embed.set_image(url="attachment://mapa_mundo.png")
        embed.set_footer(text="Use /viajar para se mover pelo mundo.")

        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="viajar", description="🐎 Viaja para uma cidade ou região conhecida.")
    @app_commands.autocomplete(destino=locais_autocomplete)
    async def viajar(self, interaction: discord.Interaction, destino: str):
        # 1. Valida Destino
        async with self.bot.db.execute("SELECT coord_x, coord_y, descricao_lore FROM locais_mundo WHERE nome = ?", (destino,)) as c:
            dest_data = await c.fetchone()
        
        if not dest_data:
            return await interaction.response.send_message(f"❌ O local **{destino}** não existe no mapa ou não foi descoberto.", ephemeral=True)
        
        dest_x, dest_y, lore = dest_data

        # 2. Pega Local Atual do Jogador
        async with self.bot.db.execute("SELECT coord_x, coord_y, localizacao_atual FROM personagens WHERE user_id=?", (interaction.user.id,)) as c:
            p_data = await c.fetchone()
        
        if not p_data: return await interaction.response.send_message("❌ Crie ficha antes.", ephemeral=True)
        p_x, p_y, p_local = p_data

        if p_local == destino:
            return await interaction.response.send_message(f"📍 Você já está em **{destino}**!", ephemeral=True)

        # 3. Calcula Viagem
        distancia = self.calcular_distancia(p_x, p_y, dest_x, dest_y)
        dias = self.obter_tempo_viagem(distancia)

        # Simulação de evento aleatório de viagem (Simples)
        msg_extra = ""
        import random
        if random.random() < 0.3: # 30% de chance
            msg_extra = "\n⚔️ **Atenção:** A estrada foi perigosa. Você avistou rastros de monstros no caminho."

        # 4. Atualiza Banco
        await self.bot.db.execute("""
            UPDATE personagens 
            SET localizacao_atual=?, coord_x=?, coord_y=? 
            WHERE user_id=?
        """, (destino, dest_x, dest_y, interaction.user.id))
        await self.bot.db.commit()

        # 5. Feedback Imersivo
        embed = discord.Embed(title=f"🐎 Viagem para {destino}", color=0x2b2d31)
        embed.description = f"Você partiu de **{p_local}** e viajou por **{dias} dias** até chegar em **{destino}**."
        embed.add_field(name="Sobre o local", value=f"_{lore}_")
        if msg_extra:
            embed.add_field(name="Evento de Estrada", value=msg_extra, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Maps(bot))