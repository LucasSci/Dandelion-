import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
import time
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.characters import Characters

class TestCharactersExportAsync(unittest.IsolatedAsyncioTestCase):
    async def test_ficha_exportar_parallel_execution(self):
        # Setup mocks
        mock_bot = MagicMock()
        mock_db = MagicMock()
        mock_bot.db = mock_db

        # Instantiate Cog
        cog = Characters(mock_bot)

        # Simulate latency
        LATENCY = 0.05

        async def delayed_fetch(*args, **kwargs):
            await asyncio.sleep(LATENCY)
            # Return tuple matching: id, nome, raca, classe, nivel, xp_atual, historia, imagem_url, ouro, hp_max, hp_atual, mp_max, ataque, defesa, vigor_max, vigor_atual, toxicidade_max, toxicidade_atual
            return (1, "Geralt", "Witcher", "Human", 10, 5000, "Story", "url", 100, 100, 100, 50, 10, 10, 100, 100, 0, 100)

        async def delayed_list_skills(*args, **kwargs):
            await asyncio.sleep(LATENCY)
            return [("Igni", "Fire", "1d6")]

        async def delayed_list_attributes(*args, **kwargs):
            await asyncio.sleep(LATENCY)
            return {"REF": 10, "INT": 10}

        async def delayed_list_armors(*args, **kwargs):
            await asyncio.sleep(LATENCY)
            return [("cabeca", 10, 100)]

        # Patch the repo methods on the instance
        cog.character_repo.fetch_export_character = AsyncMock(side_effect=delayed_fetch)
        cog.skill_repo.list_skill_export = AsyncMock(side_effect=delayed_list_skills)
        cog.character_repo.list_attributes_dict = AsyncMock(side_effect=delayed_list_attributes)
        cog.character_repo.list_armors = AsyncMock(side_effect=delayed_list_armors)

        # Mock interaction
        mock_interaction = MagicMock()
        mock_interaction.response.send_message = AsyncMock()
        mock_interaction.user.id = 123
        mock_interaction.user.display_name = "User"

        # Measure time
        start_time = time.time()

        # Call the command
        await cog.ficha_exportar.callback(cog, mock_interaction)

        end_time = time.time()
        duration = end_time - start_time

        # Verify calls were made
        cog.character_repo.fetch_export_character.assert_called_once()
        cog.skill_repo.list_skill_export.assert_called_once()
        cog.character_repo.list_attributes_dict.assert_called_once()
        cog.character_repo.list_armors.assert_called_once()

        # Verify timing indicates parallelism
        # Total latency if sequential would be ~0.2s (4 * 0.05)
        # With parallelism it should be ~0.1s (fetch + parallel group)
        # We allow some overhead but it should be definitely less than 0.18s
        self.assertLess(duration, LATENCY * 3.5, "Execution time suggests sequential execution instead of parallel")

if __name__ == "__main__":
    unittest.main()
