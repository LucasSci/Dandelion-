import unittest
from utils import rolar_dados

class TestDiceUX(unittest.TestCase):
    def test_rolar_dados_standard(self):
        # Existing behavior: 1d20 works
        detalhes, total = rolar_dados("1d20")
        self.assertIsNotNone(detalhes)
        self.assertGreaterEqual(total, 1)
        self.assertLessEqual(total, 20)

    def test_rolar_dados_standard_with_bonus(self):
        # Existing behavior: 1d20+5 works
        detalhes, total = rolar_dados("1d20+5")
        self.assertIsNotNone(detalhes)
        self.assertGreaterEqual(total, 6)
        self.assertLessEqual(total, 25)

    def test_rolar_dados_implicit_count(self):
        # New behavior: d20 works (implicitly 1d20)
        detalhes, total = rolar_dados("d20")
        self.assertIsNotNone(detalhes)
        self.assertGreaterEqual(total, 1)
        self.assertLessEqual(total, 20)
        # Check that details string is correct format, e.g. "[15]"
        self.assertTrue(detalhes.startswith("[") and detalhes.endswith("]"))

    def test_rolar_dados_implicit_count_with_bonus(self):
        # New behavior: d20+5 works
        detalhes, total = rolar_dados("d20+5")
        self.assertIsNotNone(detalhes)
        self.assertGreaterEqual(total, 6)
        self.assertLessEqual(total, 25)

    def test_rolar_dados_various_dice(self):
        # d6
        d, t = rolar_dados("d6")
        self.assertIsNotNone(d)
        self.assertTrue(1 <= t <= 6)

        # d100
        d, t = rolar_dados("d100")
        self.assertIsNotNone(d)
        self.assertTrue(1 <= t <= 100)

    def test_rolar_dados_invalid_still_fails(self):
        # Random text
        d, t = rolar_dados("batata")
        self.assertIsNone(d)

        # Missing sides
        d, t = rolar_dados("1d")
        self.assertIsNone(d)

        # d without number
        d, t = rolar_dados("d")
        self.assertIsNone(d)
