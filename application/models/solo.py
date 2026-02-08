from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SoloCampaignSummary:
    capitulo: int
    progresso: int
    gancho: Optional[str]
    local_nome: Optional[str]


@dataclass(frozen=True)
class SoloAdvanceResult:
    capitulo: int
    progresso: int
    xp_ganho: int
    xp_restante: int
    niveis_subidos: int
    recurso_nome: str
    recurso_qtd: int
    local_nome: Optional[str]
