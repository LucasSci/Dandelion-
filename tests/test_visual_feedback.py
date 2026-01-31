import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.getcwd())

import discord
from ui.sheet_view import PocaoSelect, HabilidadeButton

class TestVisualFeedback(unittest.IsolatedAsyncioTestCase):
    async def test_potion_feedback_visuals(self):
        """
        Verifies that consuming a potion provides visual feedback (bar) for toxicity in the response embed.
        """
        # Mock dependencies
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock()
        mock_interaction.user.display_name = "Player"

        # Mock CharacterRepository
        # We patch it where it is imported in ui.sheet_view
        with patch("ui.sheet_view.CharacterRepository") as MockCharRepo, \
             patch("ui.sheet_view.InventoryRepository") as MockInvRepo:

            mock_char_repo = MockCharRepo.return_value
            mock_inv_repo = MockInvRepo.return_value

            # Setup data: Current Toxicity 0, Max 100
            mock_char_repo.fetch_toxicity = AsyncMock(return_value=(0, 100))
            mock_char_repo.update_toxicity = AsyncMock()

            mock_inv_repo.delete_item = AsyncMock()

            # Potion data: ID 1, Name "Healing Potion", Effect "Restores HP"
            potions = [(1, "Healing Potion", "Restores HP")]

            # Instantiate Select
            select = PocaoSelect(potions, personagem_id=1)

            # Simulate selection
            select._values = ["1"]

            # Trigger callback
            await select.callback(mock_interaction)

            # Verify update called
            mock_char_repo.update_toxicity.assert_called_with(1, 10) # 0 + 10 = 10

            # Verify Embed content
            mock_interaction.response.send_message.assert_called_once()
            _, kwargs = mock_interaction.response.send_message.call_args
            embed = kwargs.get('embed')

            self.assertIsNotNone(embed)

            # Find Toxicity field
            toxicity_field = next((f for f in embed.fields if "Toxicidade" in f.name), None)
            self.assertIsNotNone(toxicity_field, "Toxicidade field missing")

            # Assert Visual Bar Presence (Green for low toxicity)
            # We expect '🟩' because 10/100 = 10% (Low)
            self.assertIn("🟩", toxicity_field.value, "Visual bar (Green) missing in Toxicity field")

    async def test_skill_feedback_visuals(self):
        """
        Verifies that using a skill provides visual feedback (bar) for vigor in the response embed footer.
        """
        # Mock dependencies
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock()
        mock_interaction.user.display_name = "Player"

        with patch("ui.sheet_view.CharacterRepository") as MockCharRepo, \
             patch("ui.sheet_view.rolar_dados") as mock_rolar_dados:

            mock_char_repo = MockCharRepo.return_value

            # Setup Vigor: Current 5, Max 5
            mock_char_repo.fetch_vigor = AsyncMock(return_value=(5, 5))
            mock_char_repo.update_vigor = AsyncMock()

            # Mock roll result to avoid errors
            mock_rolar_dados.return_value = ("[4]", 4)

            # Instantiate Button
            # Vigor cost 1
            btn = HabilidadeButton("Fireball", "1d6", "Boom", personagem_id=1, vigor_cost=1)

            # Trigger callback
            await btn.callback(mock_interaction)

            # Verify update called
            mock_char_repo.update_vigor.assert_called_with(1, 4) # 5 - 1 = 4

            # Verify Embed content
            mock_interaction.response.send_message.assert_called_once()
            _, kwargs = mock_interaction.response.send_message.call_args
            embed = kwargs.get('embed')

            self.assertIsNotNone(embed)

            # Verify Footer
            # We expect '🟩' because 4/5 = 80% (High Vigor)
            self.assertIsNotNone(embed.footer.text, "Footer missing")
            self.assertIn("Vigor:", embed.footer.text)
            self.assertIn("🟩", embed.footer.text, "Visual bar (Green) missing in Footer")

if __name__ == '__main__':
    unittest.main()
