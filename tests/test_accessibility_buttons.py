import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
# Mock 'utils' because ui.combat_view might not need it but cogs/combat does.
# Actually ui.combat_view imports nothing special.
from ui.combat_view import MestreView
from cogs.inventory import InventarioView

class TestAccessibilityButtons(unittest.IsolatedAsyncioTestCase):
    async def test_mestre_view_buttons(self):
        """
        Verifies that MestreView buttons use the 'emoji' parameter.
        """
        # Mock dependencies
        mock_cog = MagicMock()
        channel_id = 12345

        view = MestreView(mock_cog, channel_id)

        btn_proximo = None
        for item in view.children:
            if not isinstance(item, discord.ui.Button):
                continue
            if item.style == discord.ButtonStyle.success:
                btn_proximo = item
                break

        self.assertIsNotNone(btn_proximo, "Destravar button not found")

        # Check if emoji is set
        self.assertIsNotNone(btn_proximo.emoji, "Button emoji should be set via parameter")
        self.assertEqual(str(btn_proximo.emoji), "▶️", "Button emoji should be ▶️")

        # Check label doesn't contain the emoji
        self.assertNotIn("▶️", btn_proximo.label, "Label should not contain the emoji text")

    async def test_inventario_view_buttons(self):
        """
        Verifies that InventarioView buttons use the 'emoji' parameter.
        """
        user_id = 123
        view = InventarioView(user_id)

        btn_vender = None
        btn_fechar = None

        for item in view.children:
            if not isinstance(item, discord.ui.Button):
                continue

            if item.style == discord.ButtonStyle.success:
                btn_vender = item
            elif item.style == discord.ButtonStyle.danger:
                btn_fechar = item

        self.assertIsNotNone(btn_vender, "Vender button not found")
        self.assertIsNotNone(btn_fechar, "Fechar button not found")

        # Verify Vender Button
        self.assertIsNotNone(btn_vender.emoji, "Vender button emoji should be set")
        self.assertEqual(str(btn_vender.emoji), "💰")
        self.assertNotIn("💰", btn_vender.label, "Vender label should not contain emoji")

        # Verify Fechar Button
        self.assertIsNotNone(btn_fechar.emoji, "Fechar button emoji should be set")
        self.assertEqual(str(btn_fechar.emoji), "❌")
        self.assertNotIn("❌", btn_fechar.label, "Fechar label should not contain emoji")

if __name__ == '__main__':
    unittest.main()
