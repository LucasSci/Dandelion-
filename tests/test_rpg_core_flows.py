import unittest
from unittest.mock import patch

from rpg_core.campaign_manager import LootTable, QuestNode
from rpg_core.derived_stats import calculate_derived_stats
from rpg_core.schemas import ArmorLayer, CharacterSheet, Stats


class TestDerivedStats(unittest.TestCase):
    def test_calculate_derived_stats_with_defaults(self):
        derived = calculate_derived_stats({"BODY": 6, "WILL": 4, "REF": 5, "DEX": 3})

        self.assertEqual(derived["Stun"], 10)
        self.assertEqual(derived["Run"], 8)
        self.assertEqual(derived["Leap"], 9)
        self.assertEqual(derived["Recovery"], 5)


class TestQuestFlow(unittest.TestCase):
    def test_quest_node_progression(self):
        root = QuestNode(id="root", descricao="Inicio")
        child = QuestNode(id="child", descricao="Objetivo secundario")
        root.add_child(child)

        found = root.find_node("child")
        self.assertIs(found, child)

        child.mark_completed()
        self.assertTrue(child.concluido)


class TestLootFlow(unittest.TestCase):
    def test_generate_loot_with_region_table(self):
        table = LootTable()

        with patch("rpg_core.campaign_manager.random.sample") as sample_mock:
            sample_mock.return_value = ["couro gasto", "erva comum"]
            loot = table.generate_loot("Velen", quantidade=2)

        sample_mock.assert_called_once_with(table.region_tables["Velen"], k=2)
        self.assertEqual(loot, ["couro gasto", "erva comum"])

    def test_generate_loot_unknown_region(self):
        table = LootTable()
        loot = table.generate_loot("Skellige", quantidade=2)

        self.assertEqual(loot, [])


class TestCombatFlow(unittest.TestCase):
    def test_apply_damage_with_armor_layer(self):
        stats = Stats(INT=5, REF=5, DEX=5, BODY=6, SPD=5, EMP=5, CRA=5, WILL=4, LUCK=5)
        armor = ArmorLayer(local="torso", sp_base=10, reliability=100)
        sheet = CharacterSheet(nome="Geralt", stats=stats, armor_layers={"torso": armor})

        remaining = sheet.apply_damage("torso", 4)

        self.assertEqual(remaining, 0)
        self.assertEqual(sheet.armor_layers["torso"].sp_current, 8)


if __name__ == "__main__":
    unittest.main()
