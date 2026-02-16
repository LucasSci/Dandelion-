import sys
import os
import unittest
from unittest.mock import AsyncMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import NovaHabilidadeModal, _criar_embed_erro_formula

class TestPaletteUX(unittest.IsolatedAsyncioTestCase):
    async def test_nova_habilidade_invalid_formula_text(self):
        """
        Verifies that inputting invalid text returns a helpful Embed suggestion.
        """
        view_pai = AsyncMock()
        modal = NovaHabilidadeModal(personagem_id=1, view_pai=view_pai)

        # Simulate user typing invalid formula
        modal.nome._value = "Teste"
        modal.dado._value = "invalid"
        modal.descricao._value = "Desc"

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client.db = AsyncMock()

        # Execute
        await modal.on_submit(mock_interaction)

        # Verify response
        mock_interaction.response.send_message.assert_called_once()
        kwargs = mock_interaction.response.send_message.call_args.kwargs

        embed = kwargs.get('embed')
        self.assertIsNotNone(embed, "Should return an embed for error")
        self.assertEqual(embed.title, "❌ Fórmula Inválida")
        # Ensure description is generic for text error, not d20 specific
        # self.assertIn("Você quis dizer `1d20`?", embed.description)
        self.assertEqual(embed.color.value, 0xED4245)

    def test_helper_suggestions(self):
        """
        Test the logic of the helper function directly.
        """
        # Case 1: d20 -> Suggest 1d20
        embed = _criar_embed_erro_formula("d20")
        self.assertIn("Você quis dizer `1d20`?", embed.description)

        # Case 2: "fireball" -> Generic help
        embed = _criar_embed_erro_formula("fireball")
        self.assertIn("Formatos Válidos", embed.fields[-1].name)
        self.assertIn("Use notação de dados", embed.fields[0].value)

    async def test_nova_habilidade_valid_formula(self):
        """
        Verifies that valid formula proceeds to DB call.
        """
        view_pai = AsyncMock()
        modal = NovaHabilidadeModal(personagem_id=1, view_pai=view_pai)

        modal.nome._value = "Teste"
        modal.dado._value = "1d20+5"
        modal.descricao._value = "Desc"

        mock_interaction = AsyncMock()
        mock_interaction.response = AsyncMock()
        mock_interaction.client.db = AsyncMock() # Mock DB

        # Patch SkillRepository to avoid real DB calls
        with patch('ui.sheet_view.SkillRepository') as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.add_skill = AsyncMock()

            await modal.on_submit(mock_interaction)

            repo_instance.add_skill.assert_called_once()
            # Expect success message (ephemeral) - it sends an Embed, not a string
            mock_interaction.response.send_message.assert_called_once()
            kwargs = mock_interaction.response.send_message.call_args.kwargs
            embed = kwargs.get('embed')
            self.assertIsNotNone(embed)
            self.assertEqual(embed.title, "✨ Habilidade Aprendida!")

if __name__ == '__main__':
    unittest.main()
