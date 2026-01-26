import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.modals import CriarFichaModal

class TestCharacterCreationUX(unittest.IsolatedAsyncioTestCase):
    async def test_create_character_embed(self):
        """
        Verifies that CriarFichaModal responds with a rich Embed upon success.
        """
        # Instantiate Modal
        modal = CriarFichaModal(target_user_id='proprio')

        # Set inputs
        modal.nome._value = "Geralt"
        modal.raca._value = "Witcher"
        modal.classe._value = "School of the Wolf"
        modal.historia._value = "A lone wolf."
        modal.imagem._value = "http://example.com/geralt.png"

        # Mock interaction and DB
        mock_interaction = AsyncMock()
        mock_interaction.user.id = 12345
        mock_interaction.client.db = AsyncMock()
        mock_interaction.response = AsyncMock()

        # Mock DB execution
        mock_interaction.client.db.execute.return_value = AsyncMock()
        mock_interaction.client.db.commit.return_value = AsyncMock()

        # Execute
        await modal.on_submit(mock_interaction)

        # Verify DB insert
        mock_interaction.client.db.execute.assert_called_once()

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        kwargs = mock_interaction.response.send_message.call_args.kwargs

        # VERIFY EMBED
        embed = kwargs.get('embed')
        self.assertIsNotNone(embed, "Response should contain an Embed")
        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.title, "✨ Personagem Criado!")
        self.assertIn("Geralt", embed.description)
        self.assertEqual(embed.color.value, 0x57F287)

        # Check Fields
        field_names = [f.name for f in embed.fields]
        self.assertIn("Raça", field_names)
        self.assertIn("Classe", field_names)

        # Check Thumbnail
        self.assertEqual(embed.thumbnail.url, "http://example.com/geralt.png")

if __name__ == '__main__':
    unittest.main()
