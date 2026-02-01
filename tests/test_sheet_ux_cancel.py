import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import AcoesHabilidadeView
from ui.views import ConfirmarExclusaoView

class TestSheetUXCancel(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_delete_skill_restores_view(self):
        """
        Verifies that clicking 'Cancelar' on ConfirmarExclusaoView restores the AcoesHabilidadeView.
        """
        # Mock dependencies
        mock_view_ficha = AsyncMock()

        # Mock Interaction for initial click
        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()

        # Instantiate the view
        skill_id=1
        nome="Fireball"
        dado="1d6"
        desc="Boom"
        view = AcoesHabilidadeView(skill_id, nome, dado, desc, mock_view_ficha)

        # 1. Trigger the delete button (which opens Confirmation)
        await view.btn_excluir.callback(mock_interaction)

        # Retrieve the confirmation view passed to edit_message
        _, kwargs = mock_interaction.response.edit_message.call_args
        sent_view = kwargs.get('view')
        self.assertIsInstance(sent_view, ConfirmarExclusaoView)

        # 2. Simulate User clicking 'Cancelar' on the Confirmation View
        # We access the 'cancel' button on the view.
        # Find the cancel button (it's the second one usually, or check label)
        cancel_btn = next(child for child in sent_view.children if child.label == "Cancelar")

        # Mock interaction for the cancel click
        mock_cancel_itx = AsyncMock()
        mock_cancel_itx.response = AsyncMock()

        # Invoke callback
        await cancel_btn.callback(mock_cancel_itx)

        # 3. Verify that the ORIGINAL view (or equivalent) is restored
        # This is where it should FAIL currently, because the default behavior is just content="❌ Ação cancelada.", view=None

        mock_cancel_itx.response.edit_message.assert_called_once()
        _, cancel_kwargs = mock_cancel_itx.response.edit_message.call_args

        restored_view = cancel_kwargs.get('view')
        restored_content = cancel_kwargs.get('content')

        # Assertions for the DESIRED behavior
        self.assertIsInstance(restored_view, AcoesHabilidadeView, "Should restore AcoesHabilidadeView on cancel")
        self.assertIn(f"Gerenciando: **{nome}**", restored_content, "Should restore the management message content")

if __name__ == '__main__':
    unittest.main()
