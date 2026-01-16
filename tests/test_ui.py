import unittest
import discord
from ui.sheet_view import HabilidadeButton

class TestHabilidadeButton(unittest.TestCase):
    def test_active_skill_with_dice(self):
        """Test that a skill with a dice formula is styled as active (Primary/Blurple) with a die emoji."""
        btn = HabilidadeButton(nome="Fireball", dado="8d6", descricao="Boom")

        self.assertEqual(btn.style, discord.ButtonStyle.primary, "Active skill should have Primary style")
        # Emoji can be a string or a partial emoji object depending on how discord.py handles it internally
        # When passed as string to __init__, it's stored as str or PartialEmoji.
        # Checking str representation is usually safe.
        self.assertEqual(str(btn.emoji), "🎲", "Active skill should have dice emoji")
        self.assertIn("Fireball (8d6)", btn.label)

    def test_passive_skill_no_dice(self):
        """Test that a skill without a dice formula is styled as passive (Secondary/Grey) with a sparkles emoji."""
        btn = HabilidadeButton(nome="Darkvision", dado="", descricao="See in dark")

        self.assertEqual(btn.style, discord.ButtonStyle.secondary, "Passive skill should have Secondary style")
        self.assertEqual(str(btn.emoji), "✨", "Passive skill should have sparkles emoji")
        self.assertEqual(btn.label, "Darkvision")

if __name__ == '__main__':
    unittest.main()
