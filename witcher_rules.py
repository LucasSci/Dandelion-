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


@dataclass(frozen=True)
class ArmorDamageResult:
    sp_base: int
    reliability_inicial: int
    sp_atual: int
    dano_reduzido: int
    dano_final: int
    novo_sp_atual: int
    nova_reliability: int
    degradou: bool


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
        total += direction * roll

        if roll == 10:
            direction = 1
        elif roll == 1:
            direction = -1

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


def calcular_dano_armadura(
    dano_base: int,
    sp_base: int,
    reliability: int | None,
    multiplicador: float = 1.0,
    aplicar_degradacao: bool = True,
) -> ArmorDamageResult:
    """Calcula SP atual, dano final e degradação de armadura.

    A degradação usa a regra de redução de SP baseada no dano bruto (dano_base).
    """
    reliability_inicial = 100 if reliability is None else reliability
    reliability_inicial = max(0, min(100, reliability_inicial))
    sp_atual = max(0, int(sp_base * (reliability_inicial / 100))) if sp_base > 0 else 0

    dano_reduzido = max(0, dano_base - sp_atual)
    dano_final = max(0, int(round(dano_reduzido * multiplicador)))

    novo_sp_atual = sp_atual
    nova_reliability = reliability_inicial
    degradou = aplicar_degradacao and sp_base > 0 and dano_base > 0
    if degradou:
        reducao_sp = max(1, dano_base // 5)
        novo_sp_atual = max(0, sp_atual - reducao_sp)
        nova_reliability = max(0, min(100, int(round((novo_sp_atual / sp_base) * 100))))

    return ArmorDamageResult(
        sp_base=sp_base,
        reliability_inicial=reliability_inicial,
        sp_atual=sp_atual,
        dano_reduzido=dano_reduzido,
        dano_final=dano_final,
        novo_sp_atual=novo_sp_atual,
        nova_reliability=nova_reliability,
        degradou=degradou,
    )
