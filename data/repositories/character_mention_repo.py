from __future__ import annotations

from typing import Optional


class CharacterMentionRepository:
    def __init__(self, db):
        self.db = db

    async def add_mention(
        self,
        personagem_id: int,
        descricao_fato: str,
        relevancia: int = 0,
        session_log_id: Optional[int] = None,
    ) -> int:
        cursor = await self.db.execute(
            """
            INSERT INTO mencoes_personagem (personagem_id, session_log_id, descricao_fato, relevancia)
            VALUES (?, ?, ?, ?)
            """,
            (personagem_id, session_log_id, descricao_fato, relevancia),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def list_mentions(self, personagem_id: int, limit: int = 5) -> list[tuple[int, str, int, str, Optional[int]]]:
        async with self.db.execute(
            """
            SELECT id, descricao_fato, relevancia, criado_em, session_log_id
            FROM mencoes_personagem
            WHERE personagem_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (personagem_id, limit),
        ) as cursor:
            return await cursor.fetchall()
