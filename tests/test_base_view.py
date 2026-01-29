import unittest
from unittest.mock import AsyncMock, MagicMock
import discord
from ui.base_view import BaseRPGView

class TestBaseRPGView(unittest.IsolatedAsyncioTestCase):
    async def test_interaction_check_owner(self):
        """Test that the owner can interact."""
        view = BaseRPGView(bot=MagicMock(), user_id_dono=123)

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 123
        interaction.user.guild_permissions.administrator = False

        result = await view.interaction_check(interaction)
        self.assertTrue(result)
        interaction.response.send_message.assert_not_called()

    async def test_interaction_check_admin(self):
        """Test that an admin can interact even if not owner."""
        view = BaseRPGView(bot=MagicMock(), user_id_dono=123)

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 456
        interaction.user.guild_permissions.administrator = True

        result = await view.interaction_check(interaction)
        self.assertTrue(result)
        interaction.response.send_message.assert_not_called()

    async def test_interaction_check_unauthorized_no_char(self):
        """Test that a stranger without a character receives the 'New Player' message."""
        view = BaseRPGView(bot=MagicMock(), user_id_dono=123)

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 999
        interaction.user.guild_permissions.administrator = False
        interaction.response.send_message = AsyncMock()

        # Mock DB: No character found
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = None

        mock_ctx = MagicMock()
        mock_ctx.__aenter__.return_value = mock_cursor

        interaction.client.db.execute.return_value = mock_ctx

        result = await view.interaction_check(interaction)
        self.assertFalse(result)

        expected_msg = (
            "⛔ **Acesso Negado**\n"
            "Esta ficha pertence a <@123>.\n"
            "✨ **Quer jogar?** Use `/criar_ficha` para começar sua aventura!"
        )
        interaction.response.send_message.assert_called_with(expected_msg, ephemeral=True)

    async def test_interaction_check_unauthorized_with_char(self):
        """Test that a stranger WITH a character receives the 'View Your Sheet' message."""
        view = BaseRPGView(bot=MagicMock(), user_id_dono=123)

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 999
        interaction.user.guild_permissions.administrator = False
        interaction.response.send_message = AsyncMock()

        # Mock DB: Character found
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = (1,)

        mock_ctx = MagicMock()
        mock_ctx.__aenter__.return_value = mock_cursor

        interaction.client.db.execute.return_value = mock_ctx

        result = await view.interaction_check(interaction)
        self.assertFalse(result)

        expected_msg = (
            "⛔ **Acesso Negado**\n"
            "Esta ficha pertence a <@123>.\n"
            "💡 **Você já tem um personagem!** Use `/ficha` para ver o seu ou `/criar_ficha` para criar um novo."
        )
        interaction.response.send_message.assert_called_with(expected_msg, ephemeral=True)
