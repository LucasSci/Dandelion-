from __future__ import annotations

import random
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands


GWENT_RISCO = {
    "casual": {"label": "Casual", "multiplier": 1.0, "npc_bonus": 0},
    "profissional": {"label": "Profissional", "multiplier": 1.5, "npc_bonus": 1},
    "alto_risco": {"label": "Alto risco", "multiplier": 2.0, "npc_bonus": 2},
}

ROWS = ("Melee", "Ranged", "Siege")
WEATHER = {
    "Melee": "Nevoeiro Cerrado",
    "Ranged": "Chuva Torrencial",
    "Siege": "Geada Cortante",
}


@dataclass(frozen=True)
class GwentCard:
    name: str
    power: int
    row: str | None
    kind: str
    description: str

    @property
    def label(self) -> str:
        if self.kind == "special":
            return f"🌧️ {self.name}"
        return f"🗡️ {self.name} ({self.row})"


def build_deck(seed_bonus: int) -> list[GwentCard]:
    base_cards = [
        GwentCard("Geralt de Rivia", 10 + seed_bonus, "Melee", "unit", "Lenda de Kaer Morhen"),
        GwentCard("Ciri", 10, "Melee", "unit", "Destino encarnado"),
        GwentCard("Lambert", 7, "Melee", "unit", "Witcher sarcástico"),
        GwentCard("Eskel", 6, "Melee", "unit", "Espada veloz"),
        GwentCard("Vesemir", 6, "Melee", "unit", "Mentor lendário"),
        GwentCard("Roach", 5, "Melee", "unit", "Fiel companheira"),
        GwentCard("Zoltan Chivay", 5, "Melee", "unit", "Veterano de Mahakam"),
        GwentCard("Yennefer", 7, "Ranged", "unit", "Feiticeira de Vengerberg"),
        GwentCard("Triss", 6, "Ranged", "unit", "Mestre do fogo"),
        GwentCard("Philippa", 8, "Ranged", "unit", "Intrigas de Redânia"),
        GwentCard("Milva", 6, "Ranged", "unit", "Arqueira infalível"),
        GwentCard("Dandelion", 2, "Ranged", "unit", "Bardo inspirador"),
        GwentCard("Toruviel", 4, "Ranged", "unit", "Flechas élficas"),
        GwentCard("Trebuchet", 6, "Siege", "unit", "Guerra de cerco"),
        GwentCard("Catapulta", 7, "Siege", "unit", "Impacto devastador"),
        GwentCard("Ballista", 5, "Siege", "unit", "Cadência precisa"),
        GwentCard("Mangonel", 6, "Siege", "unit", "Explosões brutais"),
        GwentCard("Artilheiros de Novigrad", 4, "Siege", "unit", "Linha de fogo"),
        GwentCard("Medica de Kaedwen", 5, "Ranged", "unit", "Cuidados em batalha"),
        GwentCard("Vigiadores de Aedirn", 4, "Melee", "unit", "Defesa implacável"),
        GwentCard("Cavaleiro de Cintra", 6, "Melee", "unit", "Bravura real"),
        GwentCard("Guardião de Skellige", 5, "Melee", "unit", "Força nórdica"),
    ]
    special_cards = [
        GwentCard("Chuva Torrencial", 0, "Ranged", "special", "Reduz poder na linha"),
        GwentCard("Nevoeiro Cerrado", 0, "Melee", "special", "Reduz poder na linha"),
        GwentCard("Geada Cortante", 0, "Siege", "special", "Reduz poder na linha"),
        GwentCard("Comandante de Batalha", 0, None, "special", "Buff estratégico"),
        GwentCard("Clarão", 0, None, "special", "Limpa efeitos climáticos"),
    ]
    deck = base_cards + special_cards
    random.shuffle(deck)
    return deck


def apply_weather(power: int, row: str, weather: set[str]) -> int:
    return 1 if row in weather else power


def score_board(board: dict[str, list[GwentCard]], weather: set[str]) -> tuple[int, dict[str, int]]:
    row_totals = {}
    for row, cards in board.items():
        row_totals[row] = sum(apply_weather(card.power, row, weather) for card in cards)
    return sum(row_totals.values()), row_totals


def choose_card(hand: list[GwentCard], enemy_row_totals: dict[str, int]) -> GwentCard:
    weather_targets = [
        card for card in hand
        if card.kind == "special" and card.row in enemy_row_totals and enemy_row_totals[card.row] >= 12
    ]
    if weather_targets:
        return random.choice(weather_targets)
    specials = [card for card in hand if card.kind == "special"]
    if specials and random.random() < 0.2:
        return random.choice(specials)
    units = [card for card in hand if card.kind == "unit"]
    units.sort(key=lambda card: card.power, reverse=True)
    return units[0]


def should_pass(hand: list[GwentCard], my_total: int, enemy_total: int, rounds_won: int) -> bool:
    if not hand:
        return True
    if rounds_won == 1 and my_total >= enemy_total:
        return True
    if enemy_total - my_total >= 12 and len(hand) <= 2:
        return True
    return False


class Gwent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gwent", description="🃏 Dispute Gwent em rounds de cartas")
    @app_commands.describe(
        aposta="Valor da aposta (5-200).",
        risco="Define o nível de risco e recompensa.",
    )
    @app_commands.choices(risco=[
        app_commands.Choice(name="Casual (x1)", value="casual"),
        app_commands.Choice(name="Profissional (x1.5)", value="profissional"),
        app_commands.Choice(name="Alto risco (x2)", value="alto_risco"),
    ])
    @app_commands.checks.cooldown(1, 1800)
    async def gwent(
        self,
        interaction: discord.Interaction,
        aposta: app_commands.Range[int, 5, 200] = 20,
        risco: str = "casual",
    ):
        db = self.bot.db
        async with db.execute(
            "SELECT ouro, nivel FROM personagens WHERE user_id = ?",
            (interaction.user.id,),
        ) as cursor:
            dados = await cursor.fetchone()

        if not dados:
            return await interaction.response.send_message(
                "❌ Você precisa de uma ficha para jogar.",
                ephemeral=True,
            )

        ouro_atual, nivel = dados
        if aposta > ouro_atual:
            return await interaction.response.send_message(
                f"💸 Ouro insuficiente. Seu saldo atual é {ouro_atual}G.",
                ephemeral=True,
            )

        config = GWENT_RISCO.get(risco, GWENT_RISCO["casual"])
        player_bonus = min(2, nivel // 5)
        npc_bonus = config["npc_bonus"]

        player_deck = build_deck(player_bonus)
        npc_deck = build_deck(npc_bonus)
        player_hand = [player_deck.pop() for _ in range(10)]
        npc_hand = [npc_deck.pop() for _ in range(10)]

        rounds_log = []
        round_wins_player = 0
        round_wins_npc = 0
        weather_active: set[str] = set()

        for round_index in range(1, 4):
            player_board = {row: [] for row in ROWS}
            npc_board = {row: [] for row in ROWS}
            player_passed = False
            npc_passed = False
            turn_log = []
            first_player = "player" if random.random() < 0.5 else "npc"
            turn_owner = first_player

            for turn in range(1, 21):
                player_total, player_rows = score_board(player_board, weather_active)
                npc_total, npc_rows = score_board(npc_board, weather_active)

                if turn_owner == "player":
                    if player_passed or should_pass(player_hand, player_total, npc_total, round_wins_player):
                        player_passed = True
                        turn_log.append(f"Turno {turn}: Você passa.")
                    else:
                        card = choose_card(player_hand, npc_rows)
                        player_hand.remove(card)
                        if card.kind == "special":
                            if card.name == "Clarão":
                                weather_active.clear()
                                turn_log.append(f"Turno {turn}: Você usa {card.name} e limpa o clima.")
                            elif card.name == "Comandante de Batalha":
                                buff_card = random.choice([c for c in player_hand if c.kind == "unit"] or [card])
                                if buff_card.kind == "unit":
                                    player_hand.remove(buff_card)
                                    boosted = GwentCard(
                                        buff_card.name,
                                        buff_card.power + 3,
                                        buff_card.row,
                                        buff_card.kind,
                                        buff_card.description,
                                    )
                                    player_board[buff_card.row].append(boosted)
                                    turn_log.append(
                                        f"Turno {turn}: Você comanda {buff_card.name} (+3) na linha {buff_card.row}."
                                    )
                                else:
                                    turn_log.append(f"Turno {turn}: Você usa {card.name}, mas sem alvo.")
                            else:
                                weather_active.add(card.row)
                                turn_log.append(
                                    f"Turno {turn}: Você invoca {WEATHER[card.row]} na linha {card.row}."
                                )
                        else:
                            player_board[card.row].append(card)
                            turn_log.append(
                                f"Turno {turn}: Você joga {card.name} ({card.row}) {card.power}."
                            )
                    turn_owner = "npc"
                else:
                    if npc_passed or should_pass(npc_hand, npc_total, player_total, round_wins_npc):
                        npc_passed = True
                        turn_log.append(f"Turno {turn}: Oponente passa.")
                    else:
                        card = choose_card(npc_hand, player_rows)
                        npc_hand.remove(card)
                        if card.kind == "special":
                            if card.name == "Clarão":
                                weather_active.clear()
                                turn_log.append(f"Turno {turn}: Oponente usa Clarão e limpa o clima.")
                            elif card.name == "Comandante de Batalha":
                                buff_card = random.choice([c for c in npc_hand if c.kind == "unit"] or [card])
                                if buff_card.kind == "unit":
                                    npc_hand.remove(buff_card)
                                    boosted = GwentCard(
                                        buff_card.name,
                                        buff_card.power + 3,
                                        buff_card.row,
                                        buff_card.kind,
                                        buff_card.description,
                                    )
                                    npc_board[buff_card.row].append(boosted)
                                    turn_log.append(
                                        f"Turno {turn}: Oponente comanda {buff_card.name} (+3) na linha {buff_card.row}."
                                    )
                                else:
                                    turn_log.append(f"Turno {turn}: Oponente usa {card.name}, mas sem alvo.")
                            else:
                                weather_active.add(card.row)
                                turn_log.append(
                                    f"Turno {turn}: Oponente invoca {WEATHER[card.row]} na linha {card.row}."
                                )
                        else:
                            npc_board[card.row].append(card)
                            turn_log.append(
                                f"Turno {turn}: Oponente joga {card.name} ({card.row}) {card.power}."
                            )
                    turn_owner = "player"

                if player_passed and npc_passed:
                    break
                if not player_hand and not npc_hand:
                    break

            player_total, player_rows = score_board(player_board, weather_active)
            npc_total, npc_rows = score_board(npc_board, weather_active)

            if player_total > npc_total:
                round_wins_player += 1
                round_result = "✅ Vitória"
            elif npc_total > player_total:
                round_wins_npc += 1
                round_result = "❌ Derrota"
            else:
                round_result = "⚖️ Empate"

            rounds_log.append(
                "\n".join(
                    [
                        f"**Round {round_index}: {round_result}**",
                        f"Você {player_total} vs Oponente {npc_total}",
                        f"Linhas: Melee {player_rows['Melee']} | Ranged {player_rows['Ranged']} | Siege {player_rows['Siege']}",
                        f"Oponente: Melee {npc_rows['Melee']} | Ranged {npc_rows['Ranged']} | Siege {npc_rows['Siege']}",
                        "Eventos:",
                        *turn_log[:6],
                        *([f"...e mais {len(turn_log) - 6} jogadas."] if len(turn_log) > 6 else []),
                    ]
                )
            )

            if round_wins_player == 2 or round_wins_npc == 2:
                break
            weather_active.clear()

        if round_wins_player > round_wins_npc:
            resultado_final = "Vitória"
            delta_ouro = int(aposta * config["multiplier"])
        elif round_wins_npc > round_wins_player:
            resultado_final = "Derrota"
            delta_ouro = -aposta
        else:
            resultado_final = "Empate"
            delta_ouro = 0

        if delta_ouro != 0:
            await db.execute(
                "UPDATE personagens SET ouro = ouro + ? WHERE user_id = ?",
                (delta_ouro, interaction.user.id),
            )
            await db.commit()

        novo_ouro = ouro_atual + delta_ouro
        variacao = f"{'+' if delta_ouro >= 0 else ''}{delta_ouro}G"

        embed = discord.Embed(
            title="🃏 Gwent - Batalha de Cartas",
            description=f"**{resultado_final}** | {variacao}",
            color=0x1abc9c if delta_ouro >= 0 else 0xe74c3c,
        )
        embed.add_field(name="Aposta", value=f"{aposta}G", inline=True)
        embed.add_field(
            name="Risco",
            value=f"{config['label']} (x{config['multiplier']})",
            inline=True,
        )
        embed.add_field(
            name="Bônus",
            value=f"Você +{player_bonus} | Oponente +{npc_bonus}",
            inline=False,
        )
        embed.add_field(
            name="Placar de Rounds",
            value=f"Você {round_wins_player} x {round_wins_npc} Oponente",
            inline=False,
        )
        for resumo in rounds_log:
            embed.add_field(name="Resumo", value=resumo, inline=False)
        embed.set_footer(text=f"Saldo atual: {novo_ouro}G")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Gwent(bot))
