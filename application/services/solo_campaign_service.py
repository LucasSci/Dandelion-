from __future__ import annotations

import random
from typing import Optional

from application.models.solo import SoloAdvanceResult, SoloCampaignSummary
from application.ports.repositories import CharacterRepositoryPort, SoloRepositoryPort

RESOURCE_POOL = [
    ("Ervas Medicinais", (1, 3)),
    ("Couro de Monstro", (1, 2)),
    ("Minério Bruto", (1, 2)),
    ("Componentes Alquímicos", (1, 2)),
    ("Fragmentos Antigos", (1, 1)),
]


class SoloCampaignService:
    def __init__(self, character_repo: CharacterRepositoryPort, solo_repo: SoloRepositoryPort):
        self._character_repo = character_repo
        self._solo_repo = solo_repo

    def gerar_recompensas(self, passo: int) -> tuple[int, tuple[str, int]]:
        passo = max(1, min(passo, 5))
        xp_ganho = random.randint(30, 80) * passo
        recurso_nome, (min_qtd, max_qtd) = random.choice(RESOURCE_POOL)
        recurso_qtd = random.randint(min_qtd, max_qtd) * passo
        return xp_ganho, (recurso_nome, recurso_qtd)

    async def aplicar_xp(self, user_id: int, xp: int) -> tuple[int, int]:
        dados = await self._character_repo.fetch_progress_by_user(user_id)
        if not dados:
            return 0, 0

        nivel, xp_atual, hp_max, hp_atual, ataque = dados
        if hp_atual is None:
            hp_atual = hp_max

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

        await self._character_repo.update_progress(user_id, nivel, xp_atual, hp_max, hp_atual, ataque)
        return niveis_subidos, xp_atual

    async def buscar_resumo_campanha(self, user_id: int) -> Optional[SoloCampaignSummary]:
        existente = await self._solo_repo.fetch_campaign(user_id)
        if not existente:
            return None

        _, _, capitulo, progresso, gancho_atual, _, local_nome, _ = existente
        return SoloCampaignSummary(
            capitulo=capitulo,
            progresso=progresso,
            gancho=gancho_atual,
            local_nome=local_nome,
        )

    async def iniciar_campanha(self, user_id: int, gancho: Optional[str]) -> bool:
        personagem_info = await self._character_repo.fetch_character_id_and_location(user_id)
        if not personagem_info:
            return False

        personagem_id, localizacao_id = personagem_info
        await self._solo_repo.create_campaign(user_id, personagem_id, gancho, localizacao_id)
        await self._solo_repo.add_story_entry(
            user_id,
            1,
            "Início da jornada solo. O mundo se abre diante do personagem.",
        )
        return True

    async def avancar_campanha(self, user_id: int, passo: int) -> Optional[SoloAdvanceResult]:
        campanha = await self._solo_repo.fetch_campaign(user_id)
        if not campanha:
            return None

        passo = max(1, min(passo, 5))
        _, _, capitulo, progresso, _, _, _, _ = campanha
        progresso_ganho = passo * 20
        progresso_atual = progresso + progresso_ganho
        capitulo_novo = capitulo
        if progresso_atual >= 100:
            capitulo_novo += progresso_atual // 100
            progresso_atual = progresso_atual % 100

        personagem_info = await self._character_repo.fetch_character_id_and_location(user_id)
        if not personagem_info:
            return None
        localizacao_id = personagem_info[1] if personagem_info else None
        await self._solo_repo.update_campaign(user_id, capitulo_novo, progresso_atual, localizacao_id)

        xp_ganho, (recurso_nome, recurso_qtd) = self.gerar_recompensas(passo)
        niveis_subidos, xp_restante = await self.aplicar_xp(user_id, xp_ganho)
        await self._solo_repo.upsert_resource(user_id, recurso_nome, recurso_qtd)

        await self._solo_repo.add_story_entry(
            user_id,
            capitulo_novo,
            f"Avanço na jornada: +{xp_ganho} XP, +{recurso_qtd} {recurso_nome}.",
        )

        local_row = await self._character_repo.fetch_location_by_user(user_id)
        local_nome = local_row[1] if local_row else None

        return SoloAdvanceResult(
            capitulo=capitulo_novo,
            progresso=progresso_atual,
            xp_ganho=xp_ganho,
            xp_restante=xp_restante,
            niveis_subidos=niveis_subidos,
            recurso_nome=recurso_nome,
            recurso_qtd=recurso_qtd,
            local_nome=local_nome,
        )

    async def listar_entradas_diario(self, user_id: int, limit: int = 5) -> list[tuple[int, str, str]]:
        return await self._solo_repo.list_story_entries(user_id, limit=limit)

    async def listar_recursos(self, user_id: int) -> list[tuple[str, int]]:
        return await self._solo_repo.list_resources(user_id)
