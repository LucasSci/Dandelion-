import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
# Import the class to test
from ui.sheet_view import RolarPericiaModal

class TestSkillRollColor(unittest.IsolatedAsyncioTestCase):
    async def test_roll_colors(self):
        """
        Verifies that RolarPericiaModal sets the embed color based on the roll result.
        """
        # Test cases: (total_roll, expected_color_int)
        # Assuming DC defaults (Easy=10, Medium=15, Hard=20, Extreme=25)
        # We will use explicit DC input to be sure.

        # Colors
        RED = 0xED4245
        YELLOW = 0xFEE75C
        GREEN = 0x57F287
        GOLD = 0xFFD700
        DEFAULT = 0x2b2d31

        test_cases = [
            # Case 1: Failure (Total 5 vs DC 10) -> Red
            {"total": 5, "dc_input": "10", "expected": RED, "label": "Failure"},

            # Case 2: Marginal Success (Total 10 vs DC 10) -> Margin 0 -> Yellow
            # Logic: margem == 0 -> Vitória Marginal
            {"total": 10, "dc_input": "10", "expected": YELLOW, "label": "Marginal (0)"},

            # Case 3: Marginal Success (Total 14 vs DC 10) -> Margin 4 (<5) -> Yellow
            # Logic: margem < 5 -> Vitória Marginal?
            # Wait, let's check logic:
            # if margem < 0: Falha
            # elif margem == 0: Vitória Marginal
            # elif margem < 10: Vitória
            # So 1-9 is "Vitória".
            # BUT the _avaliar_dificuldade says:
            # if margem < 5: Vitória Marginal

            # The Modal.on_submit has DUPLICATE logic.
            # Let's test what currently happens vs what we want.
            # If I want consistent "Marginal < 5", I should enforce that.

            # For this test, I will assume the logic I see in on_submit:
            # elif margem == 0: nivel = "Vitória Marginal"
            # elif margem < 10: nivel = "Vitória"

            # So Total 14 vs DC 10 -> Margin 4 -> Vitória (Green)
            {"total": 14, "dc_input": "10", "expected": GREEN, "label": "Success (Margin 4)"},

            # Case 4: Critical (Total 25 vs DC 10) -> Margin 15 (>10) -> Critical (Gold)
            {"total": 25, "dc_input": "10", "expected": GOLD, "label": "Critical"},
        ]

        for case in test_cases:
            with self.subTest(label=case["label"]):
                # Setup Modal
                modal = RolarPericiaModal(atributo_nome="REF", atributo_valor=5)

                # Mock inputs
                # ui.TextInput values are not set via init, we must set them manually or via _value
                modal.pericia_nome._value = "TestSkill"
                modal.pericia_valor._value = "5" # Skill 5
                modal.dificuldade_input._value = case["dc_input"]

                # Mock Interaction
                mock_interaction = AsyncMock()
                mock_interaction.response = AsyncMock()
                mock_interaction.client = MagicMock()

                # Patch 'rolar_pericia_explosiva' to return our total
                # It returns (rolagens, total, direcao)
                with patch('ui.sheet_view.rolar_pericia_explosiva') as mock_roll:
                    mock_roll.return_value = ([case["total"]], case["total"], 0)

                    # Execute
                    await modal.on_submit(mock_interaction)

                    # Verify
                    mock_interaction.response.send_message.assert_called_once()
                    _, kwargs = mock_interaction.response.send_message.call_args
                    embed = kwargs.get('embed')

                    self.assertIsNotNone(embed, "Embed should be sent")

                    # Check Color
                    # We expect the DEFAULT color initially until we implement the fix
                    # So we assert equality to the EXPECTED color, knowing it will fail now.
                    self.assertEqual(embed.color.value, case["expected"],
                                     f"Failed for {case['label']}: Expected {hex(case['expected'])}, got {hex(embed.color.value)}")

if __name__ == '__main__':
    unittest.main()
