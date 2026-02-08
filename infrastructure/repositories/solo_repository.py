from __future__ import annotations

from typing import Optional

from application.ports.repositories import SoloRepositoryPort
from data.repositories import SoloRepository as SqliteSoloRepository


class SqliteSoloRepositoryAdapter(SoloRepositoryPort):
    def __init__(self, db):
        self._repo = SqliteSoloRepository(db)

    async def fetch_campaign(
        self, user_id: int
    ) -> Optional[tuple[int, int, int, int, Optional[str], Optional[int], Optional[str], Optional[str]]]:
        return await self._repo.fetch_campaign(user_id)

    async def create_campaign(
        self, user_id: int, personagem_id: int, gancho: Optional[str], localizacao_id: Optional[int]
    ) -> None:
        await self._repo.create_campaign(user_id, personagem_id, gancho, localizacao_id)

    async def update_campaign(self, user_id: int, capitulo: int, progresso: int, localizacao_id: Optional[int]) -> None:
        await self._repo.update_campaign(user_id, capitulo, progresso, localizacao_id)

    async def add_story_entry(self, user_id: int, capitulo: int, texto: str) -> None:
        await self._repo.add_story_entry(user_id, capitulo, texto)

    async def upsert_resource(self, user_id: int, recurso_nome: str, recurso_qtd: int) -> None:
        await self._repo.upsert_resource(user_id, recurso_nome, recurso_qtd)

    async def list_story_entries(self, user_id: int, limit: int = 5) -> list[tuple[int, str, str]]:
        return await self._repo.list_story_entries(user_id, limit=limit)

    async def list_resources(self, user_id: int) -> list[tuple[str, int]]:
        return await self._repo.list_resources(user_id)
