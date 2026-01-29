import unittest
import sys
import os

# Ensure root is in path
sys.path.append(os.getcwd())

from utils import gerar_barra

class TestVisualBar(unittest.TestCase):
    def test_full_health_green(self):
        """100% Health should be full green bar."""
        # 10/10 -> 100% -> Green
        bar = gerar_barra(10, 10, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟩🟩🟩🟩🟩]")

    def test_high_health_green(self):
        """80% Health should be mostly green bar."""
        # 8/10 -> 80% -> Green (> 70%)
        # 8/10 * 5 = 4 segments
        bar = gerar_barra(8, 10, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟩🟩🟩🟩⬛]")

    def test_medium_health_yellow(self):
        """50% Health should be half yellow bar."""
        # 5/10 -> 50% -> Yellow (> 30%)
        # 5/10 * 10 = 5 segments
        bar = gerar_barra(5, 10, segmentos=10, cor=True)
        self.assertEqual(bar, "[🟨🟨🟨🟨🟨⬛⬛⬛⬛⬛]")

    def test_low_health_red(self):
        """20% Health should be red bar."""
        # 2/10 -> 20% -> Red (<= 30%)
        # 2/10 * 5 = 1 segment
        bar = gerar_barra(2, 10, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟥⬛⬛⬛⬛]")

    def test_zero_health(self):
        """0% Health should be empty bar."""
        bar = gerar_barra(0, 10, segmentos=5, cor=True)
        self.assertEqual(bar, "[⬛⬛⬛⬛⬛]")

    def test_almost_dead(self):
        """1 HP should show at least 1 block, red."""
        # 1/100 -> 1%. 1% * 5 = 0.05 -> rounds to 0.
        # Logic ensures at least 1 block if > 0.
        bar = gerar_barra(1, 100, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟥⬛⬛⬛⬛]")

    def test_almost_full(self):
        """99/100 HP should show at least 1 empty block if requested logic was implemented...
        Wait, logic: if atual < maximo and cheio == segmentos -> cheio = segmentos - 1.
        """
        # 99/100 -> 0.99 * 5 = 4.95 -> rounds to 5.
        # But it's not full, so it should show 1 empty.
        bar = gerar_barra(99, 100, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟩🟩🟩🟩⬛]")

    def test_blue_bar(self):
        """Non-colored bar should use Blue."""
        # 5/10 = 0.5. 0.5 * 5 = 2.5. round(2.5) = 2 in Python 3.
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

    def test_rounding_half(self):
        """Check rounding behavior for 50% on odd segments."""
        # 5/10 = 0.5. 0.5 * 5 = 2.5. round(2.5) -> 2.
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

if __name__ == '__main__':
    unittest.main()
