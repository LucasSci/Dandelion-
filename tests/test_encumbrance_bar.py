import sys
import os
import unittest

# Ensure root is in path
sys.path.append(os.getcwd())

from ui.sheet_view import _gerar_barra_encumbrance

class TestEncumbranceBar(unittest.TestCase):
    def test_zero_capacity(self):
        """Test with 0 capacity."""
        bar = _gerar_barra_encumbrance(5, 0)
        self.assertEqual(bar, "⬛" * 10)

    def test_empty_load(self):
        """Test with 0 load."""
        bar = _gerar_barra_encumbrance(0, 10)
        self.assertEqual(bar, "⬛" * 10)

    def test_low_load(self):
        """Test with 20% load (Green)."""
        bar = _gerar_barra_encumbrance(2, 10)
        self.assertEqual(bar, "🟩🟩⬛⬛⬛⬛⬛⬛⬛⬛")

    def test_half_load(self):
        """Test with 50% load (Yellow)."""
        bar = _gerar_barra_encumbrance(5, 10)
        self.assertEqual(bar, "🟨🟨🟨🟨🟨⬛⬛⬛⬛⬛")

    def test_heavy_load(self):
        """Test with 80% load (Orange)."""
        bar = _gerar_barra_encumbrance(8, 10)
        self.assertEqual(bar, "🟧🟧🟧🟧🟧🟧🟧🟧⬛⬛")

    def test_full_load(self):
        """Test with 100% load (Red)."""
        bar = _gerar_barra_encumbrance(10, 10)
        self.assertEqual(bar, "🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥")

    def test_overload(self):
        """Test with >100% load (Red)."""
        bar = _gerar_barra_encumbrance(15, 10)
        self.assertEqual(bar, "🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥")

if __name__ == '__main__':
    unittest.main()
