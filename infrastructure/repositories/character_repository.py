from __future__ import annotations

from typing import Optional

from application.ports.repositories import CharacterRepositoryPort
from data.repositories import CharacterRepository as SqliteCharacterRepository


class SqliteCharacterRepositoryAdapter(CharacterRepositoryPort):
    def __init__(self, db):
        self._repo = SqliteCharacterRepository(db)

    async def fetch_progress_by_user(self, user_id: int) -> Optional[tuple[int, int, int, int, int]]:
        return await self._repo.fetch_progress_by_user(user_id)

    async def update_progress(
        self, user_id: int, nivel: int, xp_atual: int, hp_max: int, hp_atual: int, ataque: int
    ) -> None:
        await self._repo.update_progress(user_id, nivel, xp_atual, hp_max, hp_atual, ataque)

    async def fetch_character_id_and_location(self, user_id: int) -> Optional[tuple[int, Optional[int]]]:
        return await self._repo.fetch_character_id_and_location(user_id)

    async def fetch_location_by_user(self, user_id: int) -> Optional[tuple[str, Optional[str]]]:
        return await self._repo.fetch_location_by_user(user_id)
