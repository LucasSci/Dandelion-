import discord
from discord import ui
from ui.design_system import themed_embed, DEFAULT_TOKENS

class GuideSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Início",
                value="home",
                description="Bem-vindo ao Dandelion",
                emoji="🏠"
            ),
            discord.SelectOption(
                label="Para Jogadores",
                value="players",
                description="Como criar ficha, inventário, etc.",
                emoji="👤"
            ),
            discord.SelectOption(
                label="Para Mestres",
                value="gms",
                description="NPCs, combate, XP e recompensas.",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="Sistemas",
                value="systems",
                description="Atributos, perícias e dados.",
                emoji="🎲"
            ),
            discord.SelectOption(
                label="Combate",
                value="combat",
                description="Como funciona a iniciativa e ações.",
                emoji="⚔️"
            ),
        ]
        super().__init__(placeholder="Escolha um tópico de ajuda...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: GuideView = self.view
        embed = view.get_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


class GuideView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(GuideSelect())

    def get_embed(self, category: str) -> discord.Embed:
        if category == "players":
            embed = themed_embed("👤 Guia para Jogadores", "Tudo que você precisa para começar sua jornada.")
            embed.add_field(
                name="1. Criando Personagem",
                value="Use `/criar_ficha` para iniciar. Você receberá um formulário para preencher nome, classe e origem.",
                inline=False
            )
            embed.add_field(
                name="2. Seu Painel",
                value="Use `/ficha` para abrir seu painel interativo. Lá você gerencia atributos, equipamentos e perícias.",
                inline=False
            )
            embed.add_field(
                name="3. Inventário e Loja",
                value="• `/inventario`: Vê seus itens.\n• `/loja`: Compra equipamentos (se houver loja no local).",
                inline=False
            )
            embed.add_field(
                name="4. Rolando Dados",
                value="Use `/rolar` (ex: `/rolar 1d20+5`). Se tiver ficha, pode usar atalhos como `/rolar pericia:Espadas`.",
                inline=False
            )
            return embed

        elif category == "gms":
            embed = themed_embed("🛡️ Guia para Mestres", "Ferramentas para narrar e gerenciar o jogo.")
            embed.add_field(
                name="Gestão de Jogadores",
                value="• `/mestre_add_xp`: Dá XP e processa níveis.\n• `/mestre_ouro`: Dá ou remove dinheiro.",
                inline=False
            )
            embed.add_field(
                name="NPCs e Criaturas",
                value="• `/npc_criar`: Cria um NPC persistente.\n• `/npc_falar`: Interage via IA.\n• `/combate_criar`: Prepara um encontro.",
                inline=False
            )
            embed.add_field(
                name="Loja e Itens",
                value="• `/loja_gerar`: Cria itens aleatórios com IA.\n• `/loja_adicionar`: Cria item customizado.",
                inline=False
            )
            return embed

        elif category == "systems":
            embed = themed_embed("🎲 Sistemas do Jogo", "Regras automatizadas pelo bot.")
            embed.add_field(
                name="Atributos e Perícias",
                value="O sistema baseia-se em `1d10 + Atributo + Perícia`. O bot calcula tudo automaticamente na `/ficha`.",
                inline=False
            )
            embed.add_field(
                name="Sorte e Vigor",
                value="• **Vigor**: Usado para magia e esforços extras.\n• **Sorte**: Pode ser gasta para re-rolar testes ou salvar a vida.",
                inline=False
            )
            embed.add_field(
                name="Artesanato e Alquimia",
                value="Você pode coletar diagramas e fórmulas. Use o menu de 'Artesanato' na `/ficha` para criar itens.",
                inline=False
            )
            return embed

        elif category == "combat":
            embed = themed_embed("⚔️ Sistema de Combate", "Como lutar e sobreviver.")
            embed.add_field(
                name="Iniciando",
                value="O Mestre usa `/combate_criar` e `/combate_iniciar`. Jogadores usam `/combate_entrar` para participar.",
                inline=False
            )
            embed.add_field(
                name="Turnos",
                value="O bot gerencia a Iniciativa. Quando for sua vez, botões de Ação (Ataque, Defesa, Magia) aparecerão.",
                inline=False
            )
            embed.add_field(
                name="Dano e Armadura",
                value="O dano é calculado automaticamente considerando a Armadura (SP) do alvo e resistências.",
                inline=False
            )
            return embed

        else: # Home
            embed = themed_embed("🏠 Bem-vindo ao Dandelion", "Seu assistente para RPGs no universo de The Witcher.")
            embed.description = (
                "Eu ajudo a gerenciar fichas, rolagens, inventários e combates.\n\n"
                "**Por onde começar?**\n"
                "Selecione uma categoria abaixo para aprender mais sobre minhas funções."
            )
            embed.add_field(
                name="🤖 Recursos de IA",
                value="Eu uso inteligência artificial para gerar descrições de itens, narrar combates e interpretar NPCs!",
                inline=False
            )
            return embed
