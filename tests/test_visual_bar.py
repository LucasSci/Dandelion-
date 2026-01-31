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
        # 8/10 -> 80% -> Green (> 60%)
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
        """1 HP (1%) results in 1 segment minimum to show life."""
        # 1/100 -> 1%. Rule: If > 0, min 1 segment.
        bar = gerar_barra(1, 100, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟥⬛⬛⬛⬛]")

    def test_almost_full(self):
        """99/100 HP (99%) results in 4 segments (max-1 rule)."""
        # 99/100 -> 99%. Rule: If < max, max segments-1.
        bar = gerar_barra(99, 100, segmentos=5, cor=True)
        self.assertEqual(bar, "[🟩🟩🟩🟩⬛]")

    def test_blue_bar(self):
        """Explicit cor=False should result in blue bar."""
        # 5/10 = 0.5 -> Blue because cor=False
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

    def test_rounding_half(self):
        """Check int rounding for 50% on odd segments with blue color."""
        # 5/10 = 0.5. 0.5 * 5 = 2.5. round(2.5) -> 2.
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

if __name__ == '__main__':
    unittest.main()
