from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class Stats:
    INT: int
    REF: int
    DEX: int
    BODY: int
    SPD: int
    EMP: int
    CRA: int
    WILL: int
    LUCK: int


@dataclass
class DerivedStats:
    stats: Stats
    stun: int = 0
    run: int = 0
    leap: int = 0
    hp: int = 0
    stamina: int = 0
    vigor: int = 0
    recovery: int = 0

    def __post_init__(self) -> None:
        if self.stun <= 0:
            self.stun = self.stats.BODY + self.stats.WILL
        if self.run <= 0:
            self.run = self.stats.SPD * 3
        if self.leap <= 0:
            self.leap = max(1, int(self.stats.SPD * 1.5))
        if self.hp <= 0:
            self.hp = self.stats.BODY * 5
        if self.stamina <= 0:
            self.stamina = self.stats.BODY + self.stats.WILL
        if self.vigor <= 0:
            self.vigor = self.stats.BODY + self.stats.WILL + self.stats.EMP
        if self.recovery <= 0:
            self.recovery = max(1, self.stats.BODY // 2)


@dataclass
class SkillEntry:
    nome: str
    stat_base: str
    pontos_investidos: int
    modificadores: int = 0

    @property
    def total(self) -> int:
        return self.pontos_investidos + self.modificadores


@dataclass
class SkillTree:
    skills: List[SkillEntry] = field(default_factory=list)

    def add_skill(self, entry: SkillEntry) -> None:
        self.skills.append(entry)

    def find(self, nome: str) -> SkillEntry | None:
        for skill in self.skills:
            if skill.nome == nome:
                return skill
        return None


@dataclass
class ArmorLayer:
    local: str
    sp_base: int
    reliability: int = 100
    sp_current: int = field(init=False)

    def __post_init__(self) -> None:
        self.sp_current = self._calculate_sp_current()

    def apply_damage(self, damage: int) -> int:
        mitigated = min(self.sp_current, damage)
        remaining = damage - mitigated
        self._degrade(damage)
        return remaining

    def _degrade(self, damage: int) -> None:
        if damage <= 0:
            return
        reduction = max(1, damage // 5)
        self.reliability = max(0, self.reliability - reduction)
        self.sp_current = self._calculate_sp_current()

    def _calculate_sp_current(self) -> int:
        return max(0, int(self.sp_base * (self.reliability / 100)))


@dataclass
class WitcherToxic:
    atual: int
    maximo: int

    def add_toxicidade(self, amount: int) -> None:
        self.atual = max(0, self.atual + amount)

    def clear(self) -> None:
        self.atual = 0

    @property
    def is_overdosed(self) -> bool:
        return self.atual > self.maximo


@dataclass
class CharacterSheet:
    nome: str
    stats: Stats
    derived_stats: Optional[DerivedStats] = None
    skills: SkillTree = field(default_factory=SkillTree)
    armor_layers: Dict[str, ArmorLayer] = field(default_factory=dict)
    witcher: WitcherToxic = field(default_factory=lambda: WitcherToxic(atual=0, maximo=100))
    focus: int = 0

    def __post_init__(self) -> None:
        if self.derived_stats is None:
            self.derived_stats = DerivedStats(stats=self.stats)

    def apply_damage(self, local: str, damage: int) -> int:
        layer = self.armor_layers.get(local)
        if layer:
            return layer.apply_damage(damage)
        return damage

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)
