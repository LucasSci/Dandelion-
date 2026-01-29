import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.modals import CriarFichaModal

class TestCreationUX(unittest.IsolatedAsyncioTestCase):
    async def test_create_character_success_embed(self):
        """
        Verifies that CriarFichaModal sends a rich embed upon success.
        """
        # Instantiate Modal
        modal = CriarFichaModal(target_user_id='proprio')

        # Set inputs
        modal.nome._value = "Geralt"
        modal.raca._value = "Witcher"
        modal.classe._value = "Warrior"
        modal.historia._value = "A monster hunter."
        modal.imagem._value = "http://example.com/geralt.png"

        # Mock interaction
        mock_interaction = AsyncMock()
        mock_interaction.user.id = 12345
        mock_interaction.client.db.execute = AsyncMock()
        mock_interaction.client.db.commit = AsyncMock()
        mock_interaction.response.send_message = AsyncMock()

        # Execute
        await modal.on_submit(mock_interaction)

        # Verify DB call
        mock_interaction.client.db.execute.assert_called_once()

        # Verify Response
        mock_interaction.response.send_message.assert_called_once()

        # Check arguments
        kwargs = mock_interaction.response.send_message.call_args.kwargs
        embed = kwargs.get('embed')

        # This assertion is expected to fail initially
        self.assertIsNotNone(embed, "Response should contain an Embed")
        self.assertIn("Geralt", embed.title)
        self.assertIn("Witcher", embed.fields[0].value)
        self.assertEqual(embed.thumbnail.url, "http://example.com/geralt.png")

    async def test_archive_character_success_embed(self):
        """
        Verifies that CriarFichaModal sends a rich embed when archiving (no target user).
        """
        # Instantiate Modal with no target (Master Pool)
        modal = CriarFichaModal(target_user_id=None)

        modal.nome._value = "NPC Guard"
        modal.raca._value = "Human"
        modal.classe._value = "Guard"
        modal.historia._value = ""
        modal.imagem._value = ""

        mock_interaction = AsyncMock()
        mock_interaction.client.db.execute = AsyncMock()
        mock_interaction.client.db.commit = AsyncMock()
        mock_interaction.response.send_message = AsyncMock()

        await modal.on_submit(mock_interaction)

        kwargs = mock_interaction.response.send_message.call_args.kwargs
        embed = kwargs.get('embed')

        self.assertIsNotNone(embed, "Response should contain an Embed")
        self.assertIn("Arquivado", embed.title)
        self.assertIn("Guard", embed.fields[0].value)

if __name__ == '__main__':
    unittest.main()
