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
        Verifies that BuscarPericiaModal returns a discord.Embed with results.
        """
        # Mock dependencies
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_db = AsyncMock()
        mock_interaction.client.db = mock_db

        # Instantiate Modal
        modal = BuscarPericiaModal(personagem_id=1)
        # Simulate user input
        modal.termo._value = "Fire"

        # Mock Repository response
        # search_skills returns list of tuples: (nome, dado, descricao)
        mock_results = [
            ("Fireball", "8d6", "Explosion radius"),
            ("Fire Bolt", "1d10", "Cantrip"),
            ("Inner Fire", None, "Passive buff")
        ]

        with patch('ui.sheet_view.SkillRepository') as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.search_skills = AsyncMock(return_value=mock_results)

            # Execute on_submit
            await modal.on_submit(mock_interaction)

            # Verify Repository call
            mock_repo_instance.search_skills.assert_called_with(1, "%Fire%", limit=5)

            # Verify Response
            mock_interaction.response.send_message.assert_called_once()
            _, kwargs = mock_interaction.response.send_message.call_args

            embed = kwargs.get('embed')
            self.assertIsInstance(embed, discord.Embed, "Response should be an Embed")
            self.assertEqual(embed.title, "🔎 Resultados para 'Fire'")

            # Check Fields
            self.assertEqual(len(embed.fields), 3)

            # Field 1: Fireball (Dice)
            self.assertEqual(embed.fields[0].name, "Fireball")
            self.assertIn("🎲 8d6", embed.fields[0].value)
            self.assertIn("Explosion", embed.fields[0].value)

            # Field 3: Inner Fire (Passive)
            self.assertEqual(embed.fields[2].name, "Inner Fire")
            self.assertIn("✨ Passiva/Outros", embed.fields[2].value)

    async def test_search_no_results(self):
        """
        Verifies that empty search results return an error embed.
        """
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock()

        modal = BuscarPericiaModal(personagem_id=1)
        modal.termo._value = "Nothing"

        with patch('ui.sheet_view.SkillRepository') as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.search_skills = AsyncMock(return_value=[])

            await modal.on_submit(mock_interaction)

            mock_interaction.response.send_message.assert_called_once()
            _, kwargs = mock_interaction.response.send_message.call_args
            embed = kwargs.get('embed')

            self.assertIsInstance(embed, discord.Embed)
            self.assertIn("Nenhuma perícia encontrada", embed.title)

if __name__ == '__main__':
    unittest.main()
