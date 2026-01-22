import unittest
import sys
import os

# Ensure the project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.combat_view import gerar_barra

class TestCombatUX(unittest.TestCase):
    def test_health_bar_green(self):
        """Test that high health (> 60%) returns a green bar."""
        # 100% -> Green
        bar = gerar_barra(100, 100, tamanho=10)
        self.assertEqual(bar, "🟩" * 10)

        # 70% -> Green
        bar = gerar_barra(70, 100, tamanho=10)
        self.assertEqual(bar, "🟩" * 7 + "⬛" * 3)

    def test_health_bar_yellow(self):
        """Test that medium health (> 30% and <= 60%) returns a yellow bar."""
        # 50% -> Yellow
        bar = gerar_barra(50, 100, tamanho=10)
        self.assertEqual(bar, "🟨" * 5 + "⬛" * 5)

        # 40% -> Yellow
        bar = gerar_barra(40, 100, tamanho=10)
        self.assertEqual(bar, "🟨" * 4 + "⬛" * 6)

    def test_health_bar_red(self):
        """Test that low health (<= 30%) returns a red bar."""
        # 20% -> Red
        bar = gerar_barra(20, 100, tamanho=10)
        self.assertEqual(bar, "🟥" * 2 + "⬛" * 8)

        # 30% -> Red
        bar = gerar_barra(30, 100, tamanho=10)
        self.assertEqual(bar, "🟥" * 3 + "⬛" * 7)

    def test_health_bar_empty(self):
        """Test that 0 health returns all black squares."""
        bar = gerar_barra(0, 100, tamanho=10)
        self.assertEqual(bar, "⬛" * 10)
