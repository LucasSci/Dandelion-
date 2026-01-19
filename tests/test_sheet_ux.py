import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import AcoesHabilidadeView
from ui.views import ConfirmarExclusaoView

class TestSheetUX(unittest.IsolatedAsyncioTestCase):
    async def test_delete_skill_confirmation(self):
        """
        Verifies that clicking 'Excluir' on AcoesHabilidadeView presents a confirmation view,
        and that confirming correctly deletes the skill from the database.
        """
        # Mock dependencies
        mock_view_ficha = AsyncMock()

        # Mock Interaction
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client = MagicMock()
        mock_interaction.client.db = AsyncMock() # mock the DB connection

        # Instantiate the view
        # skill_id=1, nome="Fireball", dado="1d6", desc="Boom"
        view = AcoesHabilidadeView(1, "Fireball", "1d6", "Boom", mock_view_ficha)

        # Mock the button argument
        mock_button = MagicMock()

        # 1. Trigger the delete button
        # Invoke the button callback directly.
        # In discord.py, the decorated button's callback is a _ViewCallback wrapper
        # that handles 'self' and can be invoked with the interaction.
        await view.btn_excluir.callback(mock_interaction)

        # Verify that we edited the message to show the Confirmation View
        mock_interaction.response.edit_message.assert_called_once()
        _, kwargs = mock_interaction.response.edit_message.call_args
        sent_view = kwargs.get('view')

        self.assertIsInstance(sent_view, ConfirmarExclusaoView, "Should replace view with ConfirmarExclusaoView")
        self.assertIn("Tem certeza que deseja excluir", kwargs.get('content', ""), "Should have a warning message")

        # 2. Simulate User clicking 'Confirm' on the Confirmation View
        # The view stores the callback passed from btn_excluir
        confirm_callback = sent_view.confirm_callback

        # Mock interaction for the confirmation click
        mock_confirm_itx = AsyncMock()
        mock_confirm_itx.response = AsyncMock()
        mock_confirm_itx.client = MagicMock()
        # Mock DB for the confirmation action
        mock_db = AsyncMock()
        mock_confirm_itx.client.db = mock_db

        # Execute the callback
        await confirm_callback(mock_confirm_itx)

        # 3. Verify Logic
        # - DB Delete
        mock_db.execute.assert_called_with("DELETE FROM habilidades_personagem WHERE id = ?", (1,))
        mock_db.commit.assert_called_once()

        # - User Feedback
        mock_confirm_itx.response.edit_message.assert_called_once() # Should say "Removed"

        # - Parent View Refresh
        mock_view_ficha.atualizar_botoes_habilidade.assert_called_with(mock_confirm_itx)

if __name__ == '__main__':
    unittest.main()
