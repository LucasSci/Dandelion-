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

    async def test_interaction_check_unauthorized(self):
        """Test that a stranger receives the NEW improved error message."""
        view = BaseRPGView(bot=MagicMock(), user_id_dono=123)

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 999
        interaction.user.guild_permissions.administrator = False
        interaction.response.send_message = AsyncMock()

        result = await view.interaction_check(interaction)
        self.assertFalse(result)

        # New message check
        interaction.response.send_message.assert_called_with(
            "⛔ **Você não pode interagir aqui!**\n\nEsta ficha pertence a <@123>. Use `/criar_ficha` para criar o seu personagem.",
            ephemeral=True
        )
