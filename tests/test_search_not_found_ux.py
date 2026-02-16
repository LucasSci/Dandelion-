import sys
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import BuscarPericiaModal, NovaBuscaView

class TestSearchNotFoundUX(unittest.IsolatedAsyncioTestCase):
    async def test_search_no_results_dead_end(self):
        """
        Verifies that when no results are found, it sends an embed AND a 'Search Again' view.
        """
        # Patch SkillRepository
        with patch('ui.sheet_view.SkillRepository') as mock_repo_cls:
            # Setup mock repository instance
            mock_repo_instance = mock_repo_cls.return_value
            # Mock search_skills return value as empty list
            mock_repo_instance.search_skills = AsyncMock(return_value=[])

            # Instantiate Modal
            modal = BuscarPericiaModal(personagem_id=1)
            # Simulate input that returns nothing
            modal.termo._value = "Xyz123"

            # Mock interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock()

            # Execute
            await modal.on_submit(mock_interaction)

            # Check if send_message was called
            mock_interaction.response.send_message.assert_called_once()

            # Get arguments passed to send_message
            kwargs = mock_interaction.response.send_message.call_args.kwargs

            # Assert that 'embed' is present
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            self.assertIn("Nenhuma perícia encontrada", embed.title)

            # CRITICAL CHECK: View should be present (NovaBuscaView)
            view = kwargs.get('view')
            self.assertIsNotNone(view, "Expected a view to be present to avoid Dead End.")
            self.assertIsInstance(view, NovaBuscaView)

if __name__ == '__main__':
    unittest.main()
