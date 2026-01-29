import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import construir_embed_ficha

class TestSheetRender(unittest.IsolatedAsyncioTestCase):
    async def test_construir_embed_ficha_success(self):
        # Mock DB
        mock_db = AsyncMock()

        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo, \
             patch('ui.sheet_view.SkillRepository') as MockSkillRepo:

            char_repo = MockCharRepo.return_value
            inv_repo = MockInvRepo.return_value
            skill_repo = MockSkillRepo.return_value

            # Setup data
            # fetch_embed_details returns tuple of 19 items
            dados_simulated = (
                "Geralt", "Bruxo", "Humano", "Witcher", 10, "Story...", "img_url", 500,
                80, 100, 20, # hp_atual, hp_max, mp_max
                15, 10, 5000, # ataque, defesa, xp_atual
                20, 20, 0, 100, # vigor_atual, vigor_max, toxicidade_atual, toxicidade_max
                "Kaer Morhen" # local
            )
            char_repo.fetch_embed_details = AsyncMock(return_value=dados_simulated)

            # list_attributes returns list of tuples
            char_repo.list_attributes = AsyncMock(return_value=[("BODY", 5), ("REF", 4)])
            char_repo.calculate_derived_stats.return_value = {
                "Stun": 1, "Run": 2, "Leap": 3, "HP": 4, "Stamina": 5, "Vigor": 6, "Recovery": 7
            }

            # list_skills
            skill_repo.list_skills_for_sheet = AsyncMock(return_value=[("Igni", "1d6", "Fire")])

            # list_items
            inv_repo.list_recent_items = AsyncMock(return_value=[("Sword", "Weapon")])

            # Act
            embed = await construir_embed_ficha(mock_db, personagem_id=1, user_id=123)

            # Assert
            self.assertIsNotNone(embed)
            self.assertIsInstance(embed, discord.Embed)
            self.assertEqual(embed.title, "📜 Geralt")

            # Verify calls
            char_repo.fetch_embed_details.assert_called_with(1)
            char_repo.list_attributes.assert_called_with(1, limit=12)
            skill_repo.list_skills_for_sheet.assert_called_with(1, limit=10, order_by_name=True)
            inv_repo.list_recent_items.assert_called_with(123, limit=8)

    async def test_construir_embed_ficha_not_found(self):
        # Mock DB
        mock_db = AsyncMock()

        with patch('ui.sheet_view.CharacterRepository') as MockCharRepo, \
             patch('ui.sheet_view.InventoryRepository') as MockInvRepo, \
             patch('ui.sheet_view.SkillRepository') as MockSkillRepo:

            char_repo = MockCharRepo.return_value
            inv_repo = MockInvRepo.return_value
            skill_repo = MockSkillRepo.return_value

            char_repo.fetch_embed_details = AsyncMock(return_value=None)

            # Since we gather all of them, these need to be awaitable too!
            char_repo.list_attributes = AsyncMock(return_value=[])
            skill_repo.list_skills_for_sheet = AsyncMock(return_value=[])
            inv_repo.list_recent_items = AsyncMock(return_value=[])

            embed = await construir_embed_ficha(mock_db, personagem_id=999, user_id=123)

            self.assertIsNone(embed)

if __name__ == '__main__':
    unittest.main()
