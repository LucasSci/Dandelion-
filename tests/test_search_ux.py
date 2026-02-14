import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import BuscarPericiaModal

class TestSearchUX(unittest.IsolatedAsyncioTestCase):
    async def test_search_no_results_has_retry_button(self):
        """
        Verifies that when a search yields no results, the response includes a 'Try Again' button.
        """
        personagem_id = 123
        modal = BuscarPericiaModal(personagem_id)
        modal.termo._value = "SkillInexistente"

        # Mock interaction
        interaction = AsyncMock()
        interaction.client.db = AsyncMock()
        interaction.response = AsyncMock()

        # Patch SkillRepository in ui.sheet_view
        with patch("ui.sheet_view.SkillRepository") as MockRepoClass:
            mock_repo = MockRepoClass.return_value
            # search_skills returns empty list
            mock_repo.search_skills = AsyncMock(return_value=[])

            # Execute
            await modal.on_submit(interaction)

            # Assert response
            interaction.response.send_message.assert_called_once()
            kwargs = interaction.response.send_message.call_args.kwargs

            # Check for embed
            self.assertIn("embed", kwargs)
            embed = kwargs["embed"]
            self.assertIn("Nenhuma perícia encontrada", embed.title)

            # Check for View (the new UX feature)
            self.assertIn("view", kwargs, "Response should contain a View for navigation")
            view = kwargs["view"]
            self.assertIsInstance(view, discord.ui.View)

            # Check for button
            self.assertTrue(len(view.children) > 0, "View should have at least one button")

            button = view.children[0]
            self.assertIsInstance(button, discord.ui.Button)
            # The label is "Nova Busca" based on ui/sheet_view.py:NovaBuscaView
            self.assertTrue("Nova" in button.label or "Busca" in button.label, f"Button label '{button.label}' should clearly indicate retry")

if __name__ == "__main__":
    unittest.main()
