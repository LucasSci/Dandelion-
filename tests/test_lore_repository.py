import unittest
import sqlite3
import asyncio
from data.repositories.lore_repository import LoreRepository

class MockCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount

    async def fetchall(self):
        return self.cursor.fetchall()

    async def fetchone(self):
        return self.cursor.fetchone()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockExecuteContext:
    def __init__(self, cursor):
        self.cursor = cursor

    def __await__(self):
        # Allow "await db.execute(...)"
        async def _get_cursor():
            return self.cursor
        return _get_cursor().__await__()

    async def __aenter__(self):
        # Allow "async with db.execute(...)"
        return self.cursor

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE lore_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                resumo TEXT,
                conteudo TEXT,
                regiao TEXT DEFAULT 'Global',
                is_private BOOLEAN DEFAULT 0,
                owner_id INTEGER
            );
        """)
        self.conn.execute("""
            CREATE TABLE memoria_campanha (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                conteudo TEXT,
                data_registro TEXT DEFAULT '2023-01-01 00:00:00'
            );
        """)

    def execute(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
        return MockExecuteContext(MockCursor(cursor))

    async def commit(self):
        pass

class TestLoreRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = MockDB()
        self.repo = LoreRepository(self.db)

    async def test_add_and_get_lore(self):
        # 1. Add Velen Lore
        await self.repo.add_lore("Velen Lore", "Content", regiao="Velen")
        # 2. Add Global Lore
        await self.repo.add_lore("Global Lore", "Content", regiao="Global")

        # 3. Get Lore (Filter by Velen) - should return Velen
        rows = await self.repo.get_lore(regiao="Velen")
        titles = [r[1] for r in rows]
        self.assertIn("Velen Lore", titles)
        # Should NOT contain Global Lore? Based on my new logic:
        # If regiao != "global", query += " AND regiao LIKE ?"
        # So it matches ONLY Velen. Correct.
        self.assertNotIn("Global Lore", titles)

        # 4. Get Lore (Filter by Global) - should return ONLY Global
        rows = await self.repo.get_lore(regiao="Global")
        titles = [r[1] for r in rows]
        self.assertIn("Global Lore", titles)
        self.assertNotIn("Velen Lore", titles)

    async def test_add_and_get_events(self):
        await self.repo.add_event("Event 1", tipo="Evento")
        await self.repo.add_event("Event 2", tipo="Evento")

        events = await self.repo.get_recent_events(limit=5)
        self.assertEqual(len(events), 2)
        # Check sorted by ID ASC (repo logic)
        self.assertEqual(events[0][2], "Event 1")
        self.assertEqual(events[1][2], "Event 2")

if __name__ == "__main__":
    unittest.main()
