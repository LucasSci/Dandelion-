import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.shop import Shop, LojaView

class TestShopOptimization(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_bot = MagicMock()
        self.mock_db = MagicMock()
        self.mock_bot.db = self.mock_db
        self.mock_interaction = MagicMock()
        self.mock_interaction.response = MagicMock()
        self.mock_interaction.response.send_message = AsyncMock()
        self.mock_interaction.edit_original_response = AsyncMock()
        self.mock_interaction.response.is_done = MagicMock(return_value=False)
        self.mock_interaction.response.edit_message = AsyncMock()

        self.DELAY = 0.05

        # Create a mock cursor that sleeps when methods are called
        self.mock_cursor = AsyncMock()

        async def delayed_fetchone():
            await asyncio.sleep(self.DELAY)
            return [100] # Default return value

        async def delayed_fetchall():
            await asyncio.sleep(self.DELAY)
            return []

        self.mock_cursor.fetchone.side_effect = delayed_fetchone
        self.mock_cursor.fetchall.side_effect = delayed_fetchall

        # Mock connection context manager
        self.mock_execute_ctx = MagicMock()
        self.mock_execute_ctx.__aenter__ = AsyncMock(return_value=self.mock_cursor)
        self.mock_execute_ctx.__aexit__ = AsyncMock(return_value=None)
        self.mock_db.execute.return_value = self.mock_execute_ctx

    async def test_calcular_multiplicadores_performance(self):
        cog = Shop(self.mock_bot)

        start_time = time.time()
        await cog._calcular_multiplicadores(user_id=1, localizacao_id=1)
        duration = time.time() - start_time

        # Optimized: Parallel execution means duration should be approx DELAY (0.05s) + overhead
        # It should strictly be less than 2 * DELAY (0.10s)
        print(f"Calcular Multiplicadores Duration: {duration:.4f}s")
        self.assertLess(duration, self.DELAY * 1.5, "Optimization Failed: Execution seems sequential.")

    async def test_atualizar_comprar_performance(self):
        view = LojaView(self.mock_db, uid=123, rep_multiplier=1.0, economy_mods={})

        start_time = time.time()
        await view.atualizar_comprar(self.mock_interaction)
        duration = time.time() - start_time

        print(f"Atualizar Comprar Duration: {duration:.4f}s")
        self.assertLess(duration, self.DELAY * 1.5, "Optimization Failed: Execution seems sequential.")

    async def test_atualizar_vender_performance(self):
        view = LojaView(self.mock_db, uid=123, rep_multiplier=1.0, economy_mods={})

        start_time = time.time()
        await view.atualizar_vender(self.mock_interaction)
        duration = time.time() - start_time

        print(f"Atualizar Vender Duration: {duration:.4f}s")
        self.assertLess(duration, self.DELAY * 1.5, "Optimization Failed: Execution seems sequential.")

if __name__ == "__main__":
    unittest.main()
