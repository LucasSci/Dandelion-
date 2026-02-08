import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

# Mock aiohttp to prevent actual network calls during import if any
with patch.dict(sys.modules, {'aiohttp': MagicMock()}):
    # We need to ensure we can import the module even if dependencies are missing in the test env
    # But since we are in the sandbox, dependencies should be there.
    pass

from cogs.bestiary import Bestiary

class TestBestiaryOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_buscar_imagem_api_uses_bot_session(self):
        """
        Verifies that buscar_imagem_api uses bot.http_session instead of creating a new one.
        """
        # Mock Bot
        mock_bot = MagicMock()
        # Mock http_session
        mock_session = MagicMock()
        mock_bot.http_session = mock_session

        # Mock the response context manager
        mock_response = AsyncMock()
        mock_response.status = 200
        # Mock OpenSearch response format: [search_term, [titles], [descriptions], [urls]]
        mock_response.json.return_value = ["Griffin", ["Griffin (Creature)"], [], ["url"]]

        # The .get() method returns a context manager
        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_get_ctx

        # Instantiate Cog
        cog = Bestiary(mock_bot)

        # Call method
        # Note: buscar_imagem_api currently instantiates a new ClientSession, so this assertion will fail
        # until we optimize it.
        await cog.buscar_imagem_api("Griffin")

        # Verify bot.http_session.get was called
        mock_session.get.assert_called()

if __name__ == '__main__':
    unittest.main()
