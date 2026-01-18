import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.sheet_view import AcoesHabilidadeView, ConfirmarExclusaoView

class TestSkillConfirmation(unittest.IsolatedAsyncioTestCase):
    async def test_excluir_button_shows_confirmation(self):
        """Test that clicking Delete on Action view switches to Confirmation view."""
        # Setup
        view_ficha_mock = MagicMock()
        view = AcoesHabilidadeView(1, "Fireball", "8d6", "Boom", view_ficha_mock)

        interaction_mock = AsyncMock()
        button_mock = MagicMock()

        # Action
        # Try passing just interaction.
        # CAUTION: If the underlying function accesses 'button', this might fail if it's not passed.
        # But let's see if _ViewCallback handles it.
        await view.btn_excluir.callback(interaction_mock)

        # Verify
        interaction_mock.response.edit_message.assert_called_once()
        args, kwargs = interaction_mock.response.edit_message.call_args

        self.assertIn("Tem certeza", kwargs['content'])
        self.assertIsInstance(kwargs['view'], ConfirmarExclusaoView)

    async def test_cancel_button_returns_to_actions(self):
        """Test that clicking Cancel on Confirmation view returns to Action view."""
        # Setup
        view_ficha_mock = MagicMock()
        view = ConfirmarExclusaoView(1, "Fireball", "8d6", "Boom", view_ficha_mock)

        interaction_mock = AsyncMock()
        button_mock = MagicMock()

        # Action
        await view.btn_cancelar.callback(interaction_mock)

        # Verify
        interaction_mock.response.edit_message.assert_called_once()
        args, kwargs = interaction_mock.response.edit_message.call_args

        self.assertIn("O que deseja fazer", kwargs['content'])
        self.assertIsInstance(kwargs['view'], AcoesHabilidadeView)

    async def test_confirm_button_deletes_skill(self):
        """Test that clicking Confirm actually deletes the skill and updates UI."""
        # Setup
        view_ficha_mock = MagicMock()
        view_ficha_mock.atualizar_botoes_habilidade = AsyncMock()

        view = ConfirmarExclusaoView(1, "Fireball", "8d6", "Boom", view_ficha_mock)

        interaction_mock = AsyncMock()
        # Mock database connection
        db_mock = AsyncMock()
        interaction_mock.client.db = db_mock

        button_mock = MagicMock()

        # Action
        await view.btn_confirmar.callback(interaction_mock)

        # Verify DB delete
        db_mock.execute.assert_called_once_with("DELETE FROM habilidades_personagem WHERE id = ?", (1,))
        db_mock.commit.assert_called_once()

        # Verify UI updates
        # Should send ephemeral confirmation
        interaction_mock.response.send_message.assert_called_once()
        # Should update the main sheet buttons
        view_ficha_mock.atualizar_botoes_habilidade.assert_awaited_once_with(interaction_mock)
        # Should edit original message (the confirmation dialog)
        interaction_mock.message.edit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
