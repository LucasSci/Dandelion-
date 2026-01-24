from __future__ import annotations

from typing import Optional


class SkillRepository:
    def __init__(self, db):
        self.db = db

    async def add_skill(self, personagem_id: int, nome: str, descricao: str, dado: str) -> None:
        await self.db.execute(
            """
            INSERT INTO habilidades_personagem (personagem_id, nome, descricao, dado)
            VALUES (?, ?, ?, ?)
            """,
            (personagem_id, nome, descricao, dado),
        )
        await self.db.commit()

    async def update_skill(self, skill_id: int, nome: str, dado: str, descricao: str) -> None:
        await self.db.execute(
            """
            UPDATE habilidades_personagem
            SET nome=?, dado=?, descricao=?
            WHERE id=?
            """,
            (nome, dado, descricao, skill_id),
        )
        await self.db.commit()

    async def delete_skill(self, skill_id: int) -> None:
        await self.db.execute("DELETE FROM habilidades_personagem WHERE id = ?", (skill_id,))
        await self.db.commit()

    async def list_skills(self, personagem_id: int, limit: Optional[int] = None) -> list[tuple]:
        query = "SELECT id, nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?"
        params = [personagem_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def list_skills_for_sheet(
        self,
        personagem_id: int,
        limit: Optional[int] = None,
        order_by_name: bool = False,
    ) -> list[tuple[str, str, str]]:
        query = "SELECT nome, dado, descricao FROM habilidades_personagem WHERE personagem_id = ?"
        params = [personagem_id]
        if order_by_name:
            query += " ORDER BY nome"
        if limit:
            query += f" LIMIT {int(limit)}"
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def search_skills(self, personagem_id: int, term: str, limit: int = 5) -> list[tuple[str, str, str]]:
        async with self.db.execute(
            """
            SELECT nome, dado, descricao
            FROM habilidades_personagem
            WHERE personagem_id = ? AND nome LIKE ?
            ORDER BY nome ASC
            LIMIT ?
            """,
            (personagem_id, term, limit),
        ) as cursor:
            return await cursor.fetchall()

    async def list_skill_export(self, personagem_id: int) -> list[tuple[str, str, str]]:
        async with self.db.execute(
            "SELECT nome, descricao, dado FROM habilidades_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchall()
