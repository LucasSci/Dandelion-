import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import HabilidadeButton

class TestVigorFeedback(unittest.IsolatedAsyncioTestCase):
    async def test_insufficient_vigor_feedback(self):
        """
        Verifies that attempting to use a skill without enough vigor displays a rich Embed
        with a visual progress bar and details, instead of a plain text error.
        """
        # Mock dependencies
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock()
        mock_interaction.user.display_name = "Geralt"

        # Mock CharacterRepository
        with patch('ui.sheet_view.CharacterRepository') as MockRepo:
            repo_instance = MockRepo.return_value
            # Setup scenario: 0 Vigor current, 10 Max
            repo_instance.fetch_vigor = AsyncMock(return_value=(0, 10))

            # Instantiate Button: Cost 1
            button = HabilidadeButton(
                nome="Ignis",
                dado="1d6",
                descricao="Fire",
                personagem_id=1,
                vigor_cost=1
            )

            # Trigger callback
            await button.callback(mock_interaction)

            # Assertions
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args.kwargs

            # Check for Embed
            embed = call_kwargs.get('embed')
            self.assertIsNotNone(embed, "Should send an Embed for error feedback")
            self.assertEqual(embed.title, "⚠️ Vigor Insuficiente", "Embed title should be descriptive")
            self.assertIn("precisa de **1**", embed.description, "Description should state the cost")
            self.assertIn("tem apenas **0**", embed.description, "Description should state current amount")

            # Check for Visual Bar in fields
            field_value = embed.fields[0].value
            self.assertIn("0/10", field_value, "Field should show numeric progress")
            # Since generating the bar depends on util implementation, checking for brackets is a safe proxy for 'gerar_barra' usage
            self.assertIn("[", field_value)
            self.assertIn("]", field_value)

    async def test_sufficient_vigor_success(self):
        """
        Verifies that with sufficient vigor, the normal success flow occurs.
        """
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock()
        mock_interaction.user.display_name = "Geralt"

        with patch('ui.sheet_view.CharacterRepository') as MockRepo:
            repo_instance = MockRepo.return_value
            # Setup: 5 Vigor current, 10 Max
            repo_instance.fetch_vigor = AsyncMock(return_value=(5, 10))
            repo_instance.update_vigor = AsyncMock()

            button = HabilidadeButton(
                nome="Ignis",
                dado="1d6",
                descricao="Fire",
                personagem_id=1,
                vigor_cost=1
            )

            await button.callback(mock_interaction)

            # Assert Update was called
            repo_instance.update_vigor.assert_called_with(1, 4)

            # Assert Success Message (Embed)
            mock_interaction.response.send_message.assert_called_once()
            embed = mock_interaction.response.send_message.call_args.kwargs.get('embed')
            self.assertIn("usou Ignis", embed.title)

if __name__ == '__main__':
    unittest.main()
