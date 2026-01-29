import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import BuscarPericiaModal

class TestSearchUX(unittest.IsolatedAsyncioTestCase):
    async def test_search_results_embed(self):
        """
        Verifies that BuscarPericiaModal returns a discord.Embed with formatted results.
        """
        # Patch the SkillRepository used in sheet_view
        with patch('ui.sheet_view.SkillRepository') as MockRepoClass:
            # Setup the mock repository instance
            mock_repo = MockRepoClass.return_value
            # Setup search_skills return value: list of (nome, dado, descricao)
            mock_repo.search_skills = AsyncMock(return_value=[
                ("Bola de Fogo", "4d6", "Explosão de fogo."),
                ("Gelo", None, "Congela o alvo.")
            ])

            # Instantiate Modal
            modal = BuscarPericiaModal(personagem_id=123)
            modal.termo._value = "Fogo" # Simulate input

            # Mock interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client = MagicMock()

            # Execute
            await modal.on_submit(mock_interaction)

            # Verify
            mock_repo.search_skills.assert_called_with(123, "%Fogo%", limit=5)

            # Assert send_message was called
            mock_interaction.response.send_message.assert_called_once()

            # Check arguments
            args, kwargs = mock_interaction.response.send_message.call_args

            embed = kwargs.get('embed')
            self.assertIsNotNone(embed, "Should use discord.Embed for results")
            self.assertIsInstance(embed, discord.Embed)

            # Check Title
            self.assertIn("Resultados para 'Fogo'", embed.title)

            # Check Fields
            self.assertEqual(len(embed.fields), 2, "Should have 2 fields for 2 results")

            # First Result: Bola de Fogo (4d6) - Has dice, should use 🎲 emoji
            field1 = embed.fields[0]
            self.assertIn("🎲 Bola de Fogo", field1.name)
            self.assertIn("`4d6`", field1.name)
            self.assertIn("Explosão de fogo", field1.value)

            # Second Result: Gelo (None) - No dice, should use ✨ emoji
            field2 = embed.fields[1]
            self.assertIn("✨ Gelo", field2.name)
            self.assertIn("Congela o alvo", field2.value)

            # Check Footer
            self.assertEqual(embed.footer.text, "Use /magia para ver todas.")

if __name__ == '__main__':
    unittest.main()
