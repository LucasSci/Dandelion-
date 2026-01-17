import sys
import os
import unittest
from unittest.mock import MagicMock

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import discord
from ui.sheet_view import HabilidadeButton

class TestHabilidadeButton(unittest.TestCase):
    def test_button_style_rollable(self):
        """Test that a rollable skill (with dice) has Primary style and Dice emoji."""
        # "1d6" is truthy, so it's a rollable skill
        btn = HabilidadeButton("Fireball", "1d6", "Booms")

        self.assertEqual(btn.style, discord.ButtonStyle.primary, "Rollable skill should be Primary")
        self.assertEqual(str(btn.emoji), "🎲", "Rollable skill should have Dice emoji")

    def test_button_style_passive(self):
        """Test that a passive skill (no dice) has Secondary style and Sparkles emoji."""
        # "" is falsy, so it's a passive skill
        btn = HabilidadeButton("Insight", "", "Sees stuff")

        self.assertEqual(btn.style, discord.ButtonStyle.secondary, "Passive skill should be Secondary")
        self.assertEqual(str(btn.emoji), "✨", "Passive skill should have Sparkles emoji")

if __name__ == '__main__':
    unittest.main()
