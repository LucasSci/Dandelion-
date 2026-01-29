from __future__ import annotations

from typing import Optional


class RollsRepository:
    def __init__(self, db):
        self.db = db

    async def _next_order(self, personagem_id: int) -> int:
        async with self.db.execute(
            "SELECT COALESCE(MAX(ordem), 0) + 1 FROM rolagens_personagem WHERE personagem_id = ?",
            (personagem_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 1

    async def add_roll(
        self,
        personagem_id: int,
        nome: str,
        formula: str,
        categoria: Optional[str] = None,
        ordem: Optional[int] = None,
    ) -> int:
        ordem_final = ordem if ordem is not None else await self._next_order(personagem_id)
        cursor = await self.db.execute(
            """
            INSERT INTO rolagens_personagem (personagem_id, nome, formula, categoria, ordem)
            VALUES (?, ?, ?, ?, ?)
            """,
            (personagem_id, nome, formula, categoria, ordem_final),
        )
        await self.db.commit()
        return int(cursor.lastrowid)

    async def update_roll(
        self,
        roll_id: int,
        nome: str,
        formula: str,
        categoria: Optional[str],
        ordem: int,
    ) -> None:
        await self.db.execute(
            """
            UPDATE rolagens_personagem
            SET nome = ?, formula = ?, categoria = ?, ordem = ?
            WHERE id = ?
            """,
            (nome, formula, categoria, ordem, roll_id),
        )
        await self.db.commit()

    async def delete_roll(self, roll_id: int) -> None:
        await self.db.execute("DELETE FROM rolagens_personagem WHERE id = ?", (roll_id,))
        await self.db.commit()

    async def fetch_roll(self, roll_id: int) -> Optional[tuple[int, int, str, str, Optional[str], int]]:
        async with self.db.execute(
            """
            SELECT id, personagem_id, nome, formula, categoria, ordem
            FROM rolagens_personagem
            WHERE id = ?
            """,
            (roll_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def list_rolls(
        self,
        personagem_id: int,
        categoria: Optional[str] = None,
    ) -> list[tuple[int, str, str, Optional[str], int]]:
        query = """
            SELECT id, nome, formula, categoria, ordem
            FROM rolagens_personagem
            WHERE personagem_id = ?
        """
        params = [personagem_id]
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        query += " ORDER BY ordem ASC, nome ASC"
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()
