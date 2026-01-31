import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import time
from cogs.combat import Combat

class TestCombatXPOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_xp_application_concurrency(self):
        """Verifies that XP application for multiple players happens concurrently."""
        bot = MagicMock()
        bot.db = AsyncMock()
        bot.get_cog = MagicMock(return_value=None) # Mock AIHandler
        combat = Combat(bot)

        # Setup session with alive monster (low HP)
        channel_id = 123
        combat.sessions[channel_id] = {
            'status': 'RODANDO',
            'bloqueado': False,
            'regiao': 'Test',
            'monstros': [{'nome': 'Goblin', 'hp_max': 10, 'hp_atual': 1, 'id': 1}],
            'jogadores': [
                {'user_id': 1, 'nome': 'P1', 'hp': 10, 'hp_max': 10, 'atk': 100}, # High atk ensures kill
                {'user_id': 2, 'nome': 'P2', 'hp': 10, 'hp_max': 10, 'atk': 1},
                {'user_id': 3, 'nome': 'P3', 'hp': 10, 'hp_max': 10, 'atk': 1},
            ],
            'log': [],
            'ordem': [],
            'turno_index': 0,
            'round': 1,
            'status_effects': {}
        }

        interaction = MagicMock()
        interaction.user.id = 1
        interaction.channel_id = channel_id
        interaction.channel.send = AsyncMock()
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()

        # Mock aplicar_xp to simulate delay
        async def slow_aplicar_xp(*args, **kwargs):
            await asyncio.sleep(0.1)

        # Patch the module-level aplicar_xp function
        with patch('cogs.combat.aplicar_xp', side_effect=slow_aplicar_xp) as mock_xp:
            # Also patch _atualizar_economia_regional to avoid DB calls
            with patch.object(combat, '_atualizar_economia_regional', new_callable=AsyncMock):
                # Patch avancar_indice_turno to avoid errors
                with patch.object(combat, 'avancar_indice_turno', new_callable=AsyncMock):

                    start_time = time.time()
                    await combat.processar_acao_jogador(interaction, channel_id, "Ataque Básico")
                    end_time = time.time()

                    duration = end_time - start_time

                    # Verify calls
                    self.assertEqual(mock_xp.call_count, 3)

                    print(f"Duration: {duration:.4f}s")
                    # Should be parallelized (fast) -> ~0.1s
                    self.assertLess(duration, 0.2, "Should be parallelized (fast)")

if __name__ == '__main__':
    unittest.main()
