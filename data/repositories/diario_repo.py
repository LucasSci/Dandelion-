from __future__ import annotations


class DiarioRepository:
    def __init__(self, db):
        self.db = db

    async def list_recent_facts_by_personagem(
        self,
        personagem_id: int,
        limit: int = 5,
    ) -> list[tuple[str, int, str]]:
        async with self.db.execute(
            """
            SELECT
                COALESCE(pm.descricao_fato, sl.content) AS descricao,
                pm.relevancia,
                pm.criado_em
            FROM personagem_memorias pm
            LEFT JOIN session_logs sl ON sl.id = pm.log_id
            WHERE pm.personagem_id = ?
            ORDER BY pm.id DESC
            LIMIT ?
            """,
            (personagem_id, limit),
        ) as cursor:
            return await cursor.fetchall()
