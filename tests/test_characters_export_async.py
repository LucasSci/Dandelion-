import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import time
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.characters import Characters

class TestCharactersExportAsync(unittest.IsolatedAsyncioTestCase):
    async def test_ficha_exportar_parallelization(self):
        # Setup mocks
        mock_bot = MagicMock()
        mock_db = MagicMock()
        mock_bot.db = mock_db

        cog = Characters(mock_bot)

        # Mock interaction
        mock_interaction = MagicMock()
        mock_interaction.user.id = 123
        mock_interaction.response.send_message = AsyncMock()

        delay = 0.1

        # Define side effects as proper async functions
        async def delayed_skills(*args, **kwargs):
            await asyncio.sleep(delay)
            return []

        async def delayed_attrs(*args, **kwargs):
            await asyncio.sleep(delay)
            return {"INT": 5}

        async def delayed_armors(*args, **kwargs):
            await asyncio.sleep(delay)
            return []

        # 1. First call (must be sequential anyway)
        fake_char = [0] * 20
        fake_char[0] = 1 # ID
        fake_char[1] = "Geralt" # Name

        cog.character_repo.fetch_export_character = AsyncMock(return_value=fake_char)

        # 2. The three calls we want to parallelize
        cog.skill_repo.list_skill_export = AsyncMock(side_effect=delayed_skills)
        cog.character_repo.list_attributes_dict = AsyncMock(side_effect=delayed_attrs)
        cog.character_repo.list_armors = AsyncMock(side_effect=delayed_armors)

        start_time = time.perf_counter()

        await cog.ficha_exportar.callback(cog, mock_interaction)

        end_time = time.perf_counter()
        duration = end_time - start_time

        print(f"Duration: {duration:.4f}s")

        # If sequential: 0.1 + 0.1 + 0.1 = 0.3s minimum
        # If parallel: max(0.1, 0.1, 0.1) = 0.1s minimum
        # We assert it's closer to 0.1 than 0.3.
        self.assertLess(duration, 0.25, f"Execution time {duration:.4f}s indicates sequential processing (expected < 0.25s)")

if __name__ == "__main__":
    unittest.main()
