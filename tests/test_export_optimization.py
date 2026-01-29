import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os
import asyncio
import time
import json

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.characters import Characters

class TestExportOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_ficha_exportar_parallelism(self):
        # Setup mocks
        mock_bot = MagicMock()
        mock_bot.db = MagicMock()

        mock_interaction = MagicMock()
        mock_interaction.response = MagicMock()
        mock_interaction.response.send_message = AsyncMock()
        mock_interaction.user.id = 123
        mock_interaction.user.display_name = "TestUser"

        # Instantiate Cog
        cog = Characters(mock_bot)

        # Mock Repositories on the cog instance
        cog.character_repo = MagicMock()
        cog.skill_repo = MagicMock()
        cog.diario_repo = MagicMock()

        # Mock Data
        # fetch_export_character returns: (id, name, ...)
        # We need enough elements to avoid index error.
        # Looking at code: personagem[0], [9], [10]... [17]
        mock_character_data = [None] * 20
        mock_character_data[0] = 1 # id
        mock_character_data[1] = "Geralt" # name
        mock_character_data[9] = 50 # HP Max
        mock_character_data[14] = 50 # Stamina Max
        mock_character_data[15] = 50 # Vigor Max

        # AsyncMock with delay
        async def delayed_fetch(*args, **kwargs):
            await asyncio.sleep(0.1)
            return mock_character_data

        async def delayed_list_skills(*args, **kwargs):
            await asyncio.sleep(0.1)
            return []

        async def delayed_list_attributes(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {}

        async def delayed_list_armors(*args, **kwargs):
            await asyncio.sleep(0.1)
            return []

        cog.character_repo.fetch_export_character = AsyncMock(side_effect=delayed_fetch)
        cog.skill_repo.list_skill_export = AsyncMock(side_effect=delayed_list_skills)
        cog.character_repo.list_attributes_dict = AsyncMock(side_effect=delayed_list_attributes)
        cog.character_repo.list_armors = AsyncMock(side_effect=delayed_list_armors)

        # Measure time
        start_time = time.perf_counter()

        # Call the command callback
        # The fetch_export_character (0.1s) is sequential.
        # The other 3 (0.1s each) should be parallel.
        # Total expected optimized: ~0.2s (0.1 initial + 0.1 parallel group)
        # Total expected unoptimized: ~0.4s (0.1 + 0.1 + 0.1 + 0.1)

        await cog.ficha_exportar.callback(cog, mock_interaction)

        end_time = time.perf_counter()
        duration = end_time - start_time

        print(f"Execution time: {duration:.4f}s")

        # We expect optimization to bring it under 0.25s
        # If it's sequential, it will be around 0.4s
        self.assertLess(duration, 0.25, f"Execution took too long ({duration:.4f}s). Independent DB calls should be parallelized.")

if __name__ == "__main__":
    unittest.main()
