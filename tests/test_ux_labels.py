import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import AcoesHabilidadeView

class TestUXLabels(unittest.IsolatedAsyncioTestCase):
    async def test_acoes_habilidade_view_buttons(self):
        """
        Verifies that AcoesHabilidadeView buttons use the 'emoji' parameter
        separately from the 'label' for better accessibility and UI consistency.
        """
        # Mock dependencies
        mock_view_ficha = MagicMock()

        # Instantiate the view
        view = AcoesHabilidadeView(1, "Skill", "1d6", "Desc", mock_view_ficha)

        # Get buttons from the view items

        btn_editar = None
        btn_excluir = None

        for item in view.children:
            if not isinstance(item, discord.ui.Button):
                continue

            # Identify based on style
            # Editar is Primary (Blue)
            if item.style == discord.ButtonStyle.primary:
                btn_editar = item
            # Excluir is Danger (Red)
            elif item.style == discord.ButtonStyle.danger:
                btn_excluir = item

        self.assertIsNotNone(btn_editar, "Editar button not found")
        self.assertIsNotNone(btn_excluir, "Excluir button not found")

        # Assertions for "Editar" button
        # We expect the label to be clean text "Editar"
        self.assertEqual(btn_editar.label, "Editar", f"Button label is '{btn_editar.label}', expected 'Editar'")
        # We expect the emoji to be set explicitly
        self.assertIsNotNone(btn_editar.emoji, "Button emoji should be set via parameter")
        self.assertEqual(str(btn_editar.emoji), "✏️", "Button emoji should be ✏️")

        # Assertions for "Excluir" button
        self.assertEqual(btn_excluir.label, "Excluir", f"Button label is '{btn_excluir.label}', expected 'Excluir'")
        self.assertIsNotNone(btn_excluir.emoji, "Button emoji should be set via parameter")
        self.assertEqual(str(btn_excluir.emoji), "🗑️", "Button emoji should be 🗑️")

if __name__ == '__main__':
    unittest.main()
