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

        # Mock query results
        # The code executes multiple queries.
        # 1. Recursos (fetchOne)
        # 2. Skills (fetchAll)
        # 3. Items (fetchAll)

        # We need side_effect for fetchone/fetchall to handle sequence
        mock_cursor.fetchone.side_effect = [
            (10, 10, 0, 100), # Recursos: vigor_atual, vigor_max, tox_atual, tox_max
        ]

        # Skills (15 items)
        fake_skills = [(f"Skill {i}", "1d6", "Desc") for i in range(15)]
        # Items (empty)
        fake_items = []

        mock_cursor.fetchall.side_effect = [
            fake_skills,
            fake_items
        ]

        # Instantiate View
        view = FichaView(mock_client, personagem_id=1, user_id_dono=123)

        # Call the method WITHOUT patching add_item.
        await view.atualizar_botoes_habilidade(mock_interaction)

        # Get the sql query passed to execute. Since multiple calls happen, we check call_args_list
        # We look for the one querying skills
        found_limit = False
        for call in mock_db.execute.call_args_list:
            args, _ = call
            if "SELECT nome, dado, descricao FROM habilidades_personagem" in args[0]:
                if "LIMIT 15" in args[0].upper():
                    found_limit = True

        self.assertTrue(found_limit, "LIMIT 15 should be present in the skills query")

        # Check that we have correct number of children
        # FichaView static buttons:
        # Row 0: Geral, Combate, Magia, Atributos, Inventário (5 buttons)
        # Row 1: Buscar, Nova Skill, Gerenciar (3 buttons)
        # Total static = 8

        # Added dynamic: 15 skills.
        # Total = 23 (Safe under 25).

        self.assertEqual(len(view.children), 23)

if __name__ == "__main__":
    unittest.main()
