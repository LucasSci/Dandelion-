from __future__ import annotations
from typing import Optional, List, Tuple

class LoreRepository:
    def __init__(self, db):
        self.db = db

    async def add_lore(
        self,
        titulo: str,
        conteudo: str,
        regiao: str = "Global",
        is_private: bool = False,
        owner_id: Optional[int] = None
    ) -> int:
        resumo = conteudo[:200] + "..." if len(conteudo) > 200 else conteudo
        cursor = await self.db.execute(
            """
            INSERT INTO lore_entries (titulo, resumo, conteudo, regiao, is_private, owner_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (titulo, resumo, conteudo, regiao, int(is_private), owner_id)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_lore(
        self,
        regiao: Optional[str] = None,
        limit: int = 5,
        is_mestre: bool = False,
        user_id: Optional[int] = None
    ) -> List[Tuple[int, str, str, str, str]]:
        query = "SELECT id, titulo, resumo, conteudo, regiao FROM lore_entries WHERE 1=1"
        params = []

        # Visibility Filter
        if not is_mestre:
            query += " AND (is_private = 0 OR is_private IS NULL OR owner_id = ?)"
            params.append(user_id)

        # Region Filter
        if regiao:
            # Case insensitive comparison for region
            query += " AND regiao LIKE ?"
            params.append(regiao) # SQLite LIKE is case-insensitive by default for ASCII

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def add_event(self, conteudo: str, tipo: str = "Evento") -> int:
        cursor = await self.db.execute(
            "INSERT INTO memoria_campanha (tipo, conteudo) VALUES (?, ?)",
            (tipo, conteudo)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_recent_events(self, limit: int = 15) -> List[Tuple[int, str, str, str]]:
        # id, tipo, conteudo, data_registro
        async with self.db.execute(
            "SELECT id, tipo, conteudo, data_registro FROM memoria_campanha ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            # Return reversed to be chronological
            return sorted(rows, key=lambda x: x[0])

    async def search_lore(self, query_text: str, limit: int = 5, is_mestre: bool = False, user_id: int = None) -> List[Tuple[str, str, str]]:
        # Simple LIKE search for RAG
        # Returns titulo, resumo, conteudo
        sql = "SELECT titulo, resumo, conteudo FROM lore_entries WHERE (titulo LIKE ? OR conteudo LIKE ?)"
        params = [f"%{query_text}%", f"%{query_text}%"]

        if not is_mestre:
            sql += " AND (is_private = 0 OR is_private IS NULL OR owner_id = ?)"
            params.append(user_id)

        sql += " LIMIT ?"
        params.append(limit)

        async with self.db.execute(sql, params) as cursor:
            return await cursor.fetchall()
