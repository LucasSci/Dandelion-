
import sqlite3
import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.migrations import migrate_db

class TestDBIndexes(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()

        # Create base tables needed for migration
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rolagens_personagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                formula TEXT NOT NULL,
                categoria TEXT,
                ordem INTEGER DEFAULT 0
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS habilidades_personagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER,
                nome TEXT,
                descricao TEXT,
                dado TEXT
            );
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_indexes_are_created(self):
        """Verify that migrate_db creates the expected indexes."""
        migrate_db(self.cursor)

        indexes = {}
        for row in self.cursor.execute("PRAGMA index_list(rolagens_personagem)"):
            indexes[row[1]] = True

        self.assertIn("idx_rolagens_personagem_pid_ordem", indexes, "Index for rolls missing")

        indexes = {}
        for row in self.cursor.execute("PRAGMA index_list(habilidades_personagem)"):
            indexes[row[1]] = True

        self.assertIn("idx_habilidades_personagem_pid_nome", indexes, "Index for skills missing")

    def test_rolls_query_plan(self):
        """Verify the rolls query uses the new index."""
        migrate_db(self.cursor)

        # Populate dummy data
        self.cursor.execute("INSERT INTO rolagens_personagem (personagem_id, nome, formula, ordem) VALUES (1, 'Test', '1d20', 1)")

        # Explain query plan
        self.cursor.execute("EXPLAIN QUERY PLAN SELECT id FROM rolagens_personagem WHERE personagem_id = ? ORDER BY ordem", (1,))
        plan = self.cursor.fetchall()

        # Format of plan: (id, parent, detail) or (selectid, order, from, detail) depending on version
        # We look for "USING INDEX idx_rolagens_personagem_pid_ordem" in detail

        plan_str = str(plan)
        self.assertIn("idx_rolagens_personagem_pid_ordem", plan_str, f"Query plan did not use index: {plan_str}")

    def test_skills_query_plan(self):
        """Verify the skills query uses the new index."""
        migrate_db(self.cursor)

        # Populate dummy data
        self.cursor.execute("INSERT INTO habilidades_personagem (personagem_id, nome) VALUES (1, 'Fireball')")

        # Explain query plan for filtering
        self.cursor.execute("EXPLAIN QUERY PLAN SELECT nome FROM habilidades_personagem WHERE personagem_id = ?", (1,))
        plan = self.cursor.fetchall()

        plan_str = str(plan)
        # Note: Depending on data distribution and exact query, SQLite might choose scanning if table is tiny.
        # But for empty/small table with explicit index, it usually prefers index if it covers.
        # However, idx_habilidades_personagem_pid_nome covers (personagem_id).
        # We might see "USING INDEX idx_habilidades_personagem_pid_nome" OR "USING INDEX idx_habilidades_personagem_id" (the old one)
        # Wait, I didn't create the OLD index in setUp. So it should use mine.

        self.assertIn("idx_habilidades_personagem_pid_nome", plan_str, f"Query plan did not use index: {plan_str}")

    def test_search_skills_query_plan(self):
        """Verify the search_skills query uses the new index."""
        migrate_db(self.cursor)

        # Populate dummy data
        self.cursor.execute("INSERT INTO habilidades_personagem (personagem_id, nome) VALUES (1, 'Fireball')")

        # Explain query plan for search (like in SkillRepository.search_skills)
        # Note: We need to see if it uses the index.
        # SQLite's LIKE optimizer works with prefixes if collation is right.
        # But here query is '%term%', so it can't use index for filtering (except covering).
        # But checking if it uses it for sorting or filtering by pid.

        self.cursor.execute("EXPLAIN QUERY PLAN SELECT nome FROM habilidades_personagem WHERE personagem_id = ? AND nome LIKE ? ORDER BY nome COLLATE NOCASE", (1, '%Fire%'))
        plan = self.cursor.fetchall()

        plan_str = str(plan)
        # We hope it uses the index for personagem_id filtering at least.
        self.assertIn("idx_habilidades_personagem_pid_nome", plan_str, f"Query plan did not use index: {plan_str}")

if __name__ == "__main__":
    unittest.main()
