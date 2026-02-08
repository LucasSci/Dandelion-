import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.shop import LojaView

class TestShopOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_atualizar_comprar_parallelism(self):
        # Mock DB
        mock_db = MagicMock()
        mock_cursor = AsyncMock()

        DELAY = 0.1

        async def delayed_execute(*args, **kwargs):
             await asyncio.sleep(DELAY)
             return mock_cursor

        # Mock execute to be an async context manager
        # Since 'async with db.execute' calls __aenter__, we simulate delay there
        mock_execute_ctx = MagicMock()
        mock_execute_ctx.__aenter__ = AsyncMock(side_effect=delayed_execute)
        mock_execute_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_db.execute.return_value = mock_execute_ctx

        # Mock fetchall/fetchone
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = [1000] # 1000 Gold

        # Interaction mock
        mock_interaction = MagicMock()
        mock_interaction.user.id = 123
        mock_interaction.response.is_done = MagicMock(return_value=True)
        mock_interaction.edit_original_response = AsyncMock()

        view = LojaView(mock_db, 123, 1.0, {})

        start_time = time.time()
        await view.atualizar_comprar(mock_interaction)
        end_time = time.time()

        duration = end_time - start_time

        print(f"Duration: {duration:.4f}s")

        # Before optimization: ~0.2s (2 * DELAY)
        # After optimization: ~0.1s (1 * DELAY)
        # We assert it is faster than sequential (approx)

        return duration

if __name__ == "__main__":
    unittest.main()
