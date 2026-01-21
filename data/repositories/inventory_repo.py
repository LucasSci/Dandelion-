from __future__ import annotations

from typing import Optional


class InventoryRepository:
    def __init__(self, db):
        self.db = db

    async def list_recent_items(self, user_id: int, limit: int = 8) -> list[tuple[str, Optional[str]]]:
        async with self.db.execute(
            "SELECT nome, tipo FROM inventario WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()

    async def list_items(self, user_id: int, limit: Optional[int] = None) -> list[tuple]:
        query = "SELECT nome, tipo, valor, efeito FROM inventario WHERE user_id = ?"
        params = [user_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def list_items_with_effects(self, user_id: int) -> list[tuple[str, Optional[str], Optional[str]]]:
        async with self.db.execute(
            "SELECT nome, tipo, efeito FROM inventario WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()

    async def list_potions(self, user_id: int) -> list[tuple[int, str, Optional[str], Optional[str]]]:
        async with self.db.execute(
            "SELECT id, nome, tipo, efeito FROM inventario WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()

    async def delete_item(self, item_id: int) -> None:
        await self.db.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
        await self.db.commit()
