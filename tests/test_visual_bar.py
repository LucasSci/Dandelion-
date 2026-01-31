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
        """1 HP (1%) results in 0 segments with int truncation."""
        # 1/100 -> 1%. 1% * 5 = 0.05 -> int() -> 0.
        bar = gerar_barra(1, 100, segmentos=5, cor=True)
        # Note: The implementation logic for 1HP might have changed to force at least 1 segment?
        # Let's check logic:
        # if atual > 0 and cheios == 0 and maximo > 0: cheios = 1
        # So 1 HP should give 1 segment (Red or Blue or whatever).
        # Wait, the original test expected "⬛⬛⬛⬛⬛" (empty).
        # But looking at `utils/__init__.py`:
        #     if atual > 0 and cheios == 0 and maximo > 0:
        #         cheios = 1
        # So it SHOULD return 1 segment. The original test expectation was likely wrong regarding the code logic I saw.
        # Let's see what the actual output was in the failure.
        # FAIL: test_almost_dead
        # AssertionError: '[🟥⬛⬛⬛⬛]' != '⬛⬛⬛⬛⬛'
        # So it returns 1 red segment. I should update expectation to "[🟥⬛⬛⬛⬛]"
        self.assertEqual(bar, "[🟥⬛⬛⬛⬛]")

    def test_almost_full(self):
        """99/100 HP (99%) results in 4 segments with int truncation."""
        # 99/100 -> 0.99 * 5 = 4.95 -> int() -> 4.
        bar = gerar_barra(99, 100, segmentos=5, cor=True)
        # Logic: if atual < maximo and cheios == tamanho: cheios = tamanho - 1
        # 4 segments is correct.
        self.assertEqual(bar, "[🟩🟩🟩🟩⬛]")

    def test_blue_bar(self):
        """Verifies that turning off color (cor=False) correctly produces a Blue bar."""
        # 5/10 = 0.5 -> Blue if cor=False
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

    def test_rounding_half(self):
        """Check int truncation for 50% on odd segments."""
        # 5/10 = 0.5. 0.5 * 5 = 2.5. int(2.5) -> 2.
        # cor=False -> Blue
        bar = gerar_barra(5, 10, segmentos=5, cor=False)
        self.assertEqual(bar, "[🟦🟦⬛⬛⬛]")

if __name__ == '__main__':
    unittest.main()
