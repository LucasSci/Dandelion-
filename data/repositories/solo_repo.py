from __future__ import annotations

from typing import Optional


class SoloRepository:
    def __init__(self, db):
        self.db = db

    async def fetch_campaign(self, user_id: int) -> Optional[tuple]:
        async with self.db.execute(
            """
            SELECT s.user_id, s.personagem_id, s.capitulo, s.progresso, s.gancho,
                   s.ultima_localizacao_id, w.nome, s.ultima_acao_em
            FROM solo_campaigns s
            LEFT JOIN world_locations w ON w.id = s.ultima_localizacao_id
            WHERE s.user_id = ?
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def create_campaign(
        self,
        user_id: int,
        personagem_id: int,
        gancho: Optional[str],
        localizacao_id: Optional[int],
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO solo_campaigns (user_id, personagem_id, gancho, ultima_localizacao_id)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, personagem_id, gancho, localizacao_id),
        )
        await self.db.commit()

    async def update_campaign(
        self,
        user_id: int,
        capitulo: int,
        progresso: int,
        localizacao_id: Optional[int],
    ) -> None:
        await self.db.execute(
            """
            UPDATE solo_campaigns
            SET capitulo = ?, progresso = ?, ultima_localizacao_id = ?,
                ultima_acao_em = datetime('now')
            WHERE user_id = ?
            """,
            (capitulo, progresso, localizacao_id, user_id),
        )
        await self.db.commit()

    async def add_story_entry(self, user_id: int, capitulo: int, entrada: str) -> None:
        await self.db.execute(
            """
            INSERT INTO solo_story_entries (user_id, capitulo, entrada)
            VALUES (?, ?, ?)
            """,
            (user_id, capitulo, entrada),
        )
        await self.db.commit()

    async def list_story_entries(self, user_id: int, limit: int = 5) -> list[tuple[int, str, str]]:
        async with self.db.execute(
            """
            SELECT capitulo, entrada, criado_em
            FROM solo_story_entries
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()

    async def upsert_resource(self, user_id: int, nome: str, quantidade: int) -> None:
        await self.db.execute(
            """
            INSERT INTO solo_resources (user_id, nome, quantidade)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, nome) DO UPDATE SET
                quantidade = quantidade + excluded.quantidade,
                atualizado_em = datetime('now')
            """,
            (user_id, nome, quantidade),
        )
        await self.db.commit()

    async def list_resources(self, user_id: int, limit: int = 10) -> list[tuple[str, int]]:
        async with self.db.execute(
            """
            SELECT nome, quantidade
            FROM solo_resources
            WHERE user_id = ?
            ORDER BY quantidade DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()
