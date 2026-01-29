import unittest
from utils import gerar_barra

class TestVisualUtils(unittest.TestCase):
    def test_gerar_barra_full_health(self):
        # 100/100, size 5 -> 5 green squares
        bar = gerar_barra(100, 100, 5)
        self.assertEqual(bar, "🟩🟩🟩🟩🟩")

    def test_gerar_barra_half_health(self):
        # 50/100, size 10 -> 5 yellow squares, 5 black
        bar = gerar_barra(50, 100, 10)
        # pct = 0.5. 0.3 < pct <= 0.6 is Yellow?
        # Code: if pct > 0.6: Green. elif pct > 0.3: Yellow. else: Red.
        # 0.5 is > 0.3, so Yellow.
        self.assertEqual(bar, "🟨🟨🟨🟨🟨⬛⬛⬛⬛⬛")

    def test_gerar_barra_low_health(self):
        # 10/100, size 10 -> 1 red square, 9 black
        bar = gerar_barra(10, 100, 10)
        # pct = 0.1. <= 0.3, so Red.
        self.assertEqual(bar, "🟥⬛⬛⬛⬛⬛⬛⬛⬛⬛")

    def test_gerar_barra_zero_health(self):
        # 0/100, size 5 -> 5 black
        bar = gerar_barra(0, 100, 5)
        self.assertEqual(bar, "⬛⬛⬛⬛⬛")

    def test_gerar_barra_custom_color(self):
        # 50/100, size 10, custom color Blue
        bar = gerar_barra(50, 100, 10, cor_cheio="🟦")
        self.assertEqual(bar, "🟦🟦🟦🟦🟦⬛⬛⬛⬛⬛")

    def test_gerar_barra_invalid_max(self):
        # 10/0 -> 0%
        bar = gerar_barra(10, 0, 5)
        self.assertEqual(bar, "⬛⬛⬛⬛⬛")
