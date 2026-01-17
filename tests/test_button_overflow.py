import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock utils since we might not need its full logic and it imports things
sys.modules['utils'] = MagicMock()
sys.modules['utils'].rolar_dados = MagicMock(return_value=(None, None))

# Now import the view
try:
    from ui.sheet_view import HabilidadeButton, FichaView
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

import discord
from discord import ui

class TestButtonOverflow(unittest.IsolatedAsyncioTestCase):
    async def test_button_row_limit(self):
        """
        Verify that adding more than 5 buttons WITHOUT row=1 succeeds.
        """
        view = ui.View()

        # Simulate adding 10 skills (more than 5)
        # 5 active, 5 passive to test both styles
        skills_active = [("Active", "1d6", "Desc")] * 5
        skills_passive = [("Passive", "", "Desc")] * 5
        skills = skills_active + skills_passive

        print(f"\nAttempting to add {len(skills)} buttons...")
        try:
            for i, (nome, dado, desc) in enumerate(skills):
                btn = HabilidadeButton(nome, dado, desc)
                view.add_item(btn)
                print(f"Added button {i+1}: Style={btn.style}, Emoji={btn.emoji}")
        except ValueError as e:
            self.fail(f"Raised ValueError unexpectedly: {e}")

        # Verify children count
        self.assertEqual(len(view.children), 10, "Should have 10 buttons")

        # Verify styles
        # Active skills (first 5) should be primary + dice
        for i in range(5):
            self.assertEqual(view.children[i].style, discord.ButtonStyle.primary)
            self.assertEqual(str(view.children[i].emoji), "🎲")

        # Passive skills (next 5) should be secondary + sparkles
        for i in range(5, 10):
            self.assertEqual(view.children[i].style, discord.ButtonStyle.secondary)
            self.assertEqual(str(view.children[i].emoji), "✨")

if __name__ == '__main__':
    unittest.main()
