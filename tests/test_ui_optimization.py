import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.sheet_view import FichaView

class TestSheetOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_skills_fetch_limit(self):
        # Setup mocks
        mock_interaction = MagicMock()
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_cursor = AsyncMock()

        mock_interaction.client = mock_client
        mock_client.db = mock_db
        mock_interaction.response = MagicMock()
        mock_interaction.response.is_done.return_value = False
        mock_interaction.response.edit_message = AsyncMock()

        # Mock connection context manager
        mock_execute_ctx = MagicMock()
        mock_execute_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_execute_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_db.execute.return_value = mock_execute_ctx

        # Mock cursor.fetchall result (20 items - simulating that DB respected LIMIT 20)
        # If we return 30, the code will try to add 30 buttons and crash,
        # even if it SENT the LIMIT 20 query (because mocks don't actually run SQL).
        fake_skills = [(f"Skill {i}", "1d6", "Desc") for i in range(20)]
        mock_cursor.fetchall.return_value = fake_skills

        # Instantiate View
        view = FichaView(personagem_id=1, user_id_dono=123)

        # Call the method WITHOUT patching add_item.
        # This verifies the crash fix (row=None) because if row=1 was still there, it would crash here.
        await view.atualizar_botoes_habilidade(mock_interaction)

        # Get the sql query passed to execute
        args, _ = mock_db.execute.call_args
        sql_query = args[0]

        print(f"Executed SQL: {sql_query}")

        # Assertions for AFTER optimization
        # We expect LIMIT 20 to be present
        self.assertIn("LIMIT 20", sql_query.upper(), "LIMIT 20 should be present in the query")

        # Check that we have correct number of children
        # 5 static (info, skills, atributos, add, manage) + 20 dynamic = 25.
        # Wait, let's check FichaView structure.
        # row 0 has: Info, Skills, Atributos, Nova Skill, Gerenciar. (5 items)
        # So 5 + 20 = 25.
        self.assertEqual(len(view.children), 25)
        # 7 static (Geral, Combate, Magia/Alquimia, Inventário, Buscar, Nova Skill, Gerenciar)
        # + 20 dynamic = 27.
        self.assertEqual(len(view.children), 27)

if __name__ == "__main__":
    unittest.main()
