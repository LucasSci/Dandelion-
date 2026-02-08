import sys
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import BuscarPericiaModal, NovaBuscaView

class TestSearchUXRetry(unittest.IsolatedAsyncioTestCase):
    async def test_search_results_include_retry_view(self):
        """
        Verifies that BuscarPericiaModal returns a NovaBuscaView in the response
        to allow the user to search again easily.
        """
        # Patch SkillRepository
        with patch('ui.sheet_view.SkillRepository') as mock_repo_cls:
            mock_repo_instance = mock_repo_cls.return_value
            # Mock search_skills to return empty list (simulating no results)
            mock_repo_instance.search_skills = AsyncMock(return_value=[])

            # Instantiate Modal
            modal = BuscarPericiaModal(personagem_id=1)
            modal.termo._value = "InvalidTerm"

            # Mock interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock()

            # Execute
            await modal.on_submit(mock_interaction)

            # Check send_message arguments
            mock_interaction.response.send_message.assert_called_once()
            kwargs = mock_interaction.response.send_message.call_args.kwargs

            # Verify 'view' is present and is NovaBuscaView
            view = kwargs.get('view')
            self.assertIsNotNone(view, "Response should include a view.")
            self.assertIsInstance(view, NovaBuscaView, "View should be NovaBuscaView.")
            self.assertEqual(view.personagem_id, 1, "NovaBuscaView should have correct personnage_id.")

            # Check button in view
            self.assertTrue(len(view.children) > 0, "View should have children (buttons).")
            button = view.children[0]
            self.assertIsInstance(button, discord.ui.Button)
            self.assertEqual(button.label, "Nova Busca")

    async def test_search_success_includes_retry_view(self):
        """
        Verifies that even with successful results, the retry view is included.
        """
        with patch('ui.sheet_view.SkillRepository') as mock_repo_cls:
            mock_repo_instance = mock_repo_cls.return_value
            mock_repo_instance.search_skills = AsyncMock(return_value=[("Skill", "1d6", "Desc")])

            modal = BuscarPericiaModal(personagem_id=1)
            modal.termo._value = "Skill"
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock()

            await modal.on_submit(mock_interaction)

            mock_interaction.response.send_message.assert_called_once()
            kwargs = mock_interaction.response.send_message.call_args.kwargs
            view = kwargs.get('view')
            self.assertIsInstance(view, NovaBuscaView)

if __name__ == '__main__':
    unittest.main()
