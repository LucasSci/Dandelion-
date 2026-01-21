"""Regras de rolagem e cálculos básicos do sistema Witcher."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

Roller = Callable[[int, int], int]


@dataclass(frozen=True)
class SkillRollResult:
    total: int
    rolls: List[int]
    stat: int
    skill: int
    bonus: int


@dataclass(frozen=True)
class DamageResult:
    dano_base: int
    sp_utilizado: int
    dano_final: int
    hp_restante: int


def rolar_d10_explosivo(roller: Roller = random.randint) -> Tuple[int, List[int]]:
    """Rola 1d10 com explosão para cima (10) ou para baixo (1).

    - Se sair 10, rola novamente e soma.
    - Se sair 1, rola novamente e subtrai.
    - Continua enquanto novos resultados forem 1 ou 10.
    """
    rolls: List[int] = []

    roll = roller(1, 10)
    rolls.append(roll)
    total = roll

    if roll not in (1, 10):
        return total, rolls

    direction = 1 if roll == 10 else -1

    while roll in (1, 10):
        roll = roller(1, 10)
        rolls.append(roll)

        if roll == 10:
            total += roll
            direction = 1
            continue
        if roll == 1:
            total -= roll
            direction = -1
            continue

        total += direction * roll
        break

    return total, rolls


def rolar_pericia(stat: int, skill: int, bonus: int = 0, roller: Roller = random.randint) -> SkillRollResult:
    """Rola 1d10 explosivo + stat + skill + bonus."""
    d10_total, rolls = rolar_d10_explosivo(roller=roller)
    total = d10_total + stat + skill + bonus
    return SkillRollResult(total=total, rolls=rolls, stat=stat, skill=skill, bonus=bonus)


def aplicar_dano(
    hp_atual: int,
    dano_base: int,
    sp_armadura: int,
    multiplicador: float = 1.0,
) -> DamageResult:
    """Aplica dano considerando SP (Stopping Power) da armadura.

    O dano final nunca é menor que 0.
    """
    dano_modificado = int(dano_base * multiplicador)
    dano_final = max(0, dano_modificado - sp_armadura)
    hp_restante = max(0, hp_atual - dano_final)

    return DamageResult(
        dano_base=dano_modificado,
        sp_utilizado=sp_armadura,
        dano_final=dano_final,
        hp_restante=hp_restante,
    )
