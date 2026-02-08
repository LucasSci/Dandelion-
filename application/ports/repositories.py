from __future__ import annotations

from typing import Optional, Protocol


class CharacterRepositoryPort(Protocol):
    async def fetch_progress_by_user(self, user_id: int) -> Optional[tuple[int, int, int, int, int]]:
        ...

    async def update_progress(
        self, user_id: int, nivel: int, xp_atual: int, hp_max: int, hp_atual: int, ataque: int
    ) -> None:
        ...

    async def fetch_character_id_and_location(self, user_id: int) -> Optional[tuple[int, Optional[int]]]:
        ...

    async def fetch_location_by_user(self, user_id: int) -> Optional[tuple[str, Optional[str]]]:
        ...


class SoloRepositoryPort(Protocol):
    async def fetch_campaign(self, user_id: int) -> Optional[tuple[int, int, int, int, Optional[str], Optional[int], Optional[str], Optional[str]]]:
        ...

    async def create_campaign(
        self, user_id: int, personagem_id: int, gancho: Optional[str], localizacao_id: Optional[int]
    ) -> None:
        ...

    async def update_campaign(self, user_id: int, capitulo: int, progresso: int, localizacao_id: Optional[int]) -> None:
        ...

    async def add_story_entry(self, user_id: int, capitulo: int, texto: str) -> None:
        ...

    async def upsert_resource(self, user_id: int, recurso_nome: str, recurso_qtd: int) -> None:
        ...

    async def list_story_entries(self, user_id: int, limit: int = 5) -> list[tuple[int, str, str]]:
        ...

    async def list_resources(self, user_id: int) -> list[tuple[str, int]]:
        ...
