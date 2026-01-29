import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.characters import Characters

class TestCharactersOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_listar_fichas_limit(self):
        # Setup mocks
        mock_bot = MagicMock()
        mock_db = MagicMock()
        mock_cursor = AsyncMock()
        mock_interaction = MagicMock()

        mock_bot.db = mock_db
        mock_interaction.response = MagicMock()
        mock_interaction.response.send_message = AsyncMock()

        # Mock connection context manager
        mock_execute_ctx = MagicMock()
        mock_execute_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_execute_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_db.execute.return_value = mock_execute_ctx

        # Mock cursor.fetchall result (simulating a large dataset)
        # Even though we return fewer items here, we are checking the SQL query itself.
        mock_cursor.fetchall.return_value = [("Char1", None), ("Char2", 123)]

        # Instantiate Cog
        cog = Characters(mock_bot)

        # Call the method
        # Note: app_commands wrap the function, so we might need to access the callback if it's decorated?
        # In discord.py 2.0, @app_commands.command wraps the function but usually .callback works or calling it directly if it's a method?
        # Let's try calling it directly. If it fails because of the wrapper, we'll inspect.
        await cog.listar_fichas.callback(cog, mock_interaction)

        # Get the sql query passed to execute
        args, _ = mock_db.execute.call_args
        sql_query = args[0]

        print(f"Executed SQL: {sql_query}")

        # Assertions
        self.assertIn("LIMIT 20", sql_query.upper(), "LIMIT 20 should be present in the query to optimize performance")

    async def test_ficha_exportar_parallelism(self):
        # Setup mocks
        mock_bot = MagicMock()
        mock_db = MagicMock()
        mock_bot.db = mock_db

        # Instantiate Cog
        cog = Characters(mock_bot)

        # Mock Repository methods on the cog instance
        DELAY = 0.1

        async def delayed_skills(*args, **kwargs):
            await asyncio.sleep(DELAY)
            return []

        async def delayed_attributes(*args, **kwargs):
            await asyncio.sleep(DELAY)
            return {}

        async def delayed_armors(*args, **kwargs):
            await asyncio.sleep(DELAY)
            return []

        cog.skill_repo.list_skill_export = AsyncMock(side_effect=delayed_skills)
        cog.character_repo.list_attributes_dict = AsyncMock(side_effect=delayed_attributes)
        cog.character_repo.list_armors = AsyncMock(side_effect=delayed_armors)

        mock_char_data = (
            1, "Geralt", "Human", "Witcher", 10, 5000, "History...", "url", 100,
            100, 100, 10, 5, 5, 20, 20,
            100, 0
        )
        cog.character_repo.fetch_export_character = AsyncMock(return_value=mock_char_data)

        mock_interaction = MagicMock()
        mock_interaction.user.id = 123
        mock_interaction.response.send_message = AsyncMock()

        # Measure time
        start_time = time.time()
        await cog.ficha_exportar.callback(cog, mock_interaction)
        end_time = time.time()
        duration = end_time - start_time

        # Expect parallel execution (< 2 * DELAY)
        self.assertLess(duration, DELAY * 2.0, "Execution should be parallel (approx 0.1s), but took too long.")

if __name__ == "__main__":
    unittest.main()
