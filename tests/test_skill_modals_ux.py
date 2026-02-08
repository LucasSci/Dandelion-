import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure root is in path
sys.path.append(os.getcwd())

import discord
from ui.sheet_view import NovaHabilidadeModal, EditarHabilidadeModal, AcoesHabilidadeView

class TestSkillModalsUX(unittest.IsolatedAsyncioTestCase):
    async def test_nova_habilidade_embed(self):
        """
        Verifies that NovaHabilidadeModal sends an Embed on success.
        """
        with patch('ui.sheet_view.SkillRepository') as MockRepo:
            # Setup Mock Repo
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.add_skill = AsyncMock()

            # Instantiate Modal
            view_pai = MagicMock()
            view_pai.atualizar_botoes_habilidade = AsyncMock()
            modal = NovaHabilidadeModal(123, view_pai)

            # Set inputs
            modal.nome._value = "Igni"
            modal.dado._value = "1d6"
            modal.descricao._value = "Fire blast"

            # Mock Interaction
            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock()

            # Execute
            await modal.on_submit(mock_interaction)

            # Verify add_skill called
            mock_repo_instance.add_skill.assert_called_with(123, "Igni", "Fire blast", "1d6")

            # Verify Response
            # Should be called with embed=...
            mock_interaction.response.send_message.assert_called_once()
            kwargs = mock_interaction.response.send_message.call_args.kwargs

            # This assertion will FAIL initially because the code sends a string content, not an embed
            # We expect 'embed' to be present after our changes
            # For now, we just check call occurred. We will refine this test to require an Embed
            # *after* we implement the change, or we can write it to fail now (TDD).
            # I will write it to expect an embed, so it fails now.
            self.assertIn('embed', kwargs, "Response should contain an embed")
            embed = kwargs['embed']
            self.assertIsInstance(embed, discord.Embed)
            self.assertEqual(embed.title, "✨ Habilidade Aprendida!")
            self.assertIn("Igni", embed.fields[0].value)

    async def test_editar_habilidade_embed(self):
        """
        Verifies that EditarHabilidadeModal sends an Embed on success.
        """
        with patch('ui.sheet_view.SkillRepository') as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.update_skill = AsyncMock()

            view_pai = MagicMock()
            view_pai.atualizar_botoes_habilidade = AsyncMock()
            modal = EditarHabilidadeModal(1, "Igni", "1d6", "Fire", view_pai)

            modal.nome_input._value = "Igni Max"
            modal.dado_input._value = "2d6"
            modal.desc_input._value = "Big Fire"

            mock_interaction = AsyncMock()
            mock_interaction.response = AsyncMock()
            mock_interaction.client.db = MagicMock()

            await modal.on_submit(mock_interaction)

            mock_repo_instance.update_skill.assert_called_with(1, "Igni Max", "2d6", "Big Fire")

            mock_interaction.response.send_message.assert_called_once()
            kwargs = mock_interaction.response.send_message.call_args.kwargs

            self.assertIn('embed', kwargs, "Response should contain an embed")
            embed = kwargs['embed']
            self.assertIsInstance(embed, discord.Embed)
            self.assertEqual(embed.title, "✏️ Habilidade Atualizada!")


if __name__ == '__main__':
    unittest.main()
