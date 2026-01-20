from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class NPC:
    nome: str
    disposicao: str
    localizacao_atual: str
    ativo_no_mundo: bool = True


@dataclass
class QuestNode:
    id: str
    descricao: str
    concluido: bool = False
    children: List["QuestNode"] = field(default_factory=list)

    def add_child(self, node: "QuestNode") -> None:
        self.children.append(node)

    def find_node(self, node_id: str) -> "QuestNode" | None:
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find_node(node_id)
            if found:
                return found
        return None

    def mark_completed(self) -> None:
        self.concluido = True


@dataclass
class LootTable:
    region_tables: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "Velen": [
                "couro gasto",
                "erva comum",
                "sucata de ferro",
                "reagentes de alquimia",
            ],
            "Toussaint": [
                "vinho raro",
                "moedas de ouro",
                "armas finas",
                "joias",
            ],
        }
    )

    def generate_loot(self, region: str, quantidade: int = 2) -> List[str]:
        table = self.region_tables.get(region, [])
        if not table:
            return []
        return random.sample(table, k=min(quantidade, len(table)))
