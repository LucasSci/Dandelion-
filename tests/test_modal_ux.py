import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import RolarPericiaModal

class TestModalUX(unittest.IsolatedAsyncioTestCase):
    async def test_rolar_pericia_optional_value(self):
        """
        Verifies that RolarPericiaModal handles empty pericia_valor as 0.
        """
        # We need to ensure rolar_pericia_explosiva is mocked to verify the call
        with patch('ui.sheet_view.rolar_pericia_explosiva') as mock_rolar:
            # Setup mock return
            mock_rolar.return_value = ([5], 10, 0) # rolls, total, direction

            # Instantiate Modal
            # Atributo = 5
            modal = RolarPericiaModal("Força", 5)

            # Simulate empty input
            # discord.ui.TextInput.value is a property; we set the internal _value for testing
            modal.pericia_valor._value = ""

            # Mock interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()

            # Execute
            await modal.on_submit(mock_interaction)

            # Verify
            # It should call rolar_pericia_explosiva(stat=5, skill=0)
            mock_rolar.assert_called_with(5, 0)

            # Verify response
            mock_interaction.response.send_message.assert_called_once()
            # Inspect embed to ensure logic reflected in UI
            # call_args returns (args, kwargs)
            # send_message(embed=...)
            kwargs = mock_interaction.response.send_message.call_args.kwargs
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            # Check formula field
            # Fields: [0]=Rolagem, [1]=Fórmula, [2]=Total
            self.assertIn("1d10 + Stat(5) + Skill(0)", embed.fields[1].value)

    async def test_rolar_pericia_valid_value(self):
        """
        Verifies that RolarPericiaModal handles valid pericia_valor correctly.
        """
        with patch('ui.sheet_view.rolar_pericia_explosiva') as mock_rolar:
            mock_rolar.return_value = ([5], 13, 0)

            modal = RolarPericiaModal("Força", 5)
            modal.pericia_valor._value = "3"

            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()

            await modal.on_submit(mock_interaction)

            mock_rolar.assert_called_with(5, 3)

if __name__ == '__main__':
    unittest.main()
