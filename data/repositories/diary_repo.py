from __future__ import annotations

from typing import Optional


class DiaryRepository:
    def __init__(self, db):
        self.db = db

    async def add_character_mention(
        self,
        personagem_id: int,
        descricao_fato: str,
        relevancia: int = 0,
        session_log_id: Optional[int] = None,
        memoria_id: Optional[int] = None,
    ) -> int:
        cursor = await self.db.execute(
            """
            INSERT INTO mencoes_personagem
                (personagem_id, session_log_id, memoria_id, descricao_fato, relevancia)
            VALUES (?, ?, ?, ?, ?)
            """,
            (personagem_id, session_log_id, memoria_id, descricao_fato, relevancia),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def list_mentions_by_character(self, personagem_id: int, limit: int = 5) -> list[tuple[str, int, str, Optional[int], Optional[int]]]:
        async with self.db.execute(
            """
            SELECT descricao_fato, relevancia, criado_em, session_log_id, memoria_id
            FROM mencoes_personagem
            WHERE personagem_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (personagem_id, limit),
        ) as cursor:
            return await cursor.fetchall()

    async def list_mentions_by_user(self, user_id: int, limit: int = 5) -> list[tuple[str, str, int, str]]:
        async with self.db.execute(
            """
            SELECT p.nome, m.descricao_fato, m.relevancia, m.criado_em
            FROM mencoes_personagem m
            JOIN personagens p ON p.id = m.personagem_id
            WHERE p.user_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()
