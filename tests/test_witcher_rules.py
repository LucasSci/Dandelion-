import unittest

from witcher_rules import rolar_d10_explosivo, rolar_pericia


def make_roller(sequence):
    iterator = iter(sequence)

    def roller(_min, _max):
        return next(iterator)

    return roller


class TestRolagemExplosiva(unittest.TestCase):
    def test_explosao_para_baixo_repetida(self):
        roller = make_roller([1, 1, 2])
        total, rolls = rolar_d10_explosivo(roller=roller)

        self.assertEqual(rolls, [1, 1, 2])
        self.assertEqual(total, -2)

    def test_explosao_para_cima_repetida(self):
        roller = make_roller([10, 10, 3])
        total, rolls = rolar_d10_explosivo(roller=roller)

        self.assertEqual(rolls, [10, 10, 3])
        self.assertEqual(total, 23)

    def test_alternancia_direcao(self):
        roller = make_roller([1, 10, 1, 4])
        total, rolls = rolar_d10_explosivo(roller=roller)

        self.assertEqual(rolls, [1, 10, 1, 4])
        self.assertEqual(total, -12)

    def test_rolar_pericia_soma_bonus(self):
        roller = make_roller([10, 5])
        result = rolar_pericia(stat=2, skill=3, bonus=1, roller=roller)

        self.assertEqual(result.rolls, [10, 5])
        self.assertEqual(result.total, 21)


if __name__ == "__main__":
    unittest.main()
