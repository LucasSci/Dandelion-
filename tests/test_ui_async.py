import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import FichaView

class TestUIParallelization(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = MagicMock()
        self.bot.db = AsyncMock()
        self.personagem_id = 123
        self.user_id = 456
        self.interaction = AsyncMock()
        self.interaction.user.id = self.user_id
        self.interaction.client.db = self.bot.db
        self.interaction.response.is_done = MagicMock(return_value=False)

        # Instantiate view
        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo, \
             patch('ui.sheet_view.SkillRepository') as MockSkillRepo:

             # Setup init mocks
            MockCharRepo.return_value.fetch_embed_details = AsyncMock(return_value=None) # avoid init error if any

            self.view = FichaView(self.bot, self.personagem_id, self.user_id)

    async def test_atualizar_botoes_habilidade_runs_correctly(self):
        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo, \
             patch('ui.sheet_view.SkillRepository') as MockSkillRepo:

            # Setup return values
            mock_char_repo = MockCharRepo.return_value
            mock_inv_repo = MockInvRepo.return_value
            mock_skill_repo = MockSkillRepo.return_value

            # vigor_atual, vigor_max, toxicidade_atual, toxicidade_max
            mock_char_repo.fetch_resources = AsyncMock(return_value=(10, 20, 5, 100))
            mock_skill_repo.list_skills_for_sheet = AsyncMock(return_value=[("Fireball", "1d6", "Boom")])
            # item_id, nome, tipo, efeito
            mock_inv_repo.list_potions = AsyncMock(return_value=[(1, "Poção de Cura", "poção", "Cura 10 HP")])

            await self.view.atualizar_botoes_habilidade(self.interaction)

            # Check if repos were called
            mock_char_repo.fetch_resources.assert_called_with(self.personagem_id)
            mock_skill_repo.list_skills_for_sheet.assert_called()
            mock_inv_repo.list_potions.assert_called_with(self.user_id)

            # Check interaction
            self.interaction.response.edit_message.assert_called_once()
            args, kwargs = self.interaction.response.edit_message.call_args
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            self.assertEqual(embed.title, "✨ Magia & Alquimia")

    async def test_mostrar_combate_runs_correctly(self):
        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo:

            mock_char_repo = MockCharRepo.return_value
            mock_inv_repo = MockInvRepo.return_value

            # hp_atual, hp_max, ataque, defesa
            mock_char_repo.fetch_combat_stats = AsyncMock(return_value=(50, 100, 5, 10))
            mock_inv_repo.list_items_with_effects = AsyncMock(return_value=[("Espada", "arma", "+2 Dano")])

            await self.view.mostrar_combate(self.interaction)

            mock_char_repo.fetch_combat_stats.assert_called_with(self.personagem_id)
            mock_inv_repo.list_items_with_effects.assert_called_with(self.user_id)

            self.interaction.response.edit_message.assert_called_once()
            args, kwargs = self.interaction.response.edit_message.call_args
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            self.assertEqual(embed.title, "⚔️ Combate")

    async def test_mostrar_inventario_runs_correctly(self):
        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo:

            mock_char_repo = MockCharRepo.return_value
            mock_inv_repo = MockInvRepo.return_value

            mock_inv_repo.list_items = AsyncMock(return_value=[("Espada", "arma", 100, "Sharp")])
            mock_char_repo.fetch_level = AsyncMock(return_value=5)

            await self.view.mostrar_inventario(self.interaction)

            mock_inv_repo.list_items.assert_called_with(self.user_id)
            mock_char_repo.fetch_level.assert_called_with(self.personagem_id)

            self.interaction.response.edit_message.assert_called_once()
            args, kwargs = self.interaction.response.edit_message.call_args
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            self.assertEqual(embed.title, "🎒 Inventário")

if __name__ == '__main__':
    unittest.main()
