import sys
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import BuscarPericiaModal

class TestSearchUX(unittest.IsolatedAsyncioTestCase):
    async def test_search_results_use_embed(self):
        """
        Verifies that BuscarPericiaModal returns search results in a discord.Embed.
        """
        # Patch SkillRepository where it is imported/used in sheet_view.py
        with patch('ui.sheet_view.SkillRepository') as mock_repo_cls:
            # Setup mock repository instance
            mock_repo_instance = mock_repo_cls.return_value
            # Mock search_skills return value (list of tuples: name, dice, description)
            mock_repo_instance.search_skills = AsyncMock(return_value=[
                ("Bola de Fogo", "4d6", "Uma grande bola de fogo."),
                ("Curar Ferimentos", "1d8", "Cura um aliado.")
            ])

            # Instantiate Modal
            modal = BuscarPericiaModal(personagem_id=1)
            modal.termo._value = "Fogo" # Simulate input

            # Mock interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock() # Mock db connection

            # Execute
            await modal.on_submit(mock_interaction)

            # Verify
            mock_repo_instance.search_skills.assert_called_once()

            # Check if send_message was called
            mock_interaction.response.send_message.assert_called_once()

            # Get arguments passed to send_message
            kwargs = mock_interaction.response.send_message.call_args.kwargs

            # Assert that 'embed' is present and is an instance of discord.Embed
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed, "Search results should be sent as an Embed, not plain text.")
            self.assertIsInstance(embed, discord.Embed)

            # Optional: verify embed content
            self.assertIn("Bola de Fogo", embed.description or str(embed.fields))

if __name__ == '__main__':
    from unittest.mock import MagicMock # re-import for use inside test function if needed
    unittest.main()
