import unittest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from cogs.combat import Combat

class TestCombatOptimization(unittest.IsolatedAsyncioTestCase):
    async def test_processar_acao_jogador_performance(self):
        # Setup
        bot = MagicMock()
        bot.db = AsyncMock()
        bot.get_channel = MagicMock()

        # Mock AI Handler with delay
        ai_handler = AsyncMock()
        async def delayed_narrative(*args, **kwargs):
            await asyncio.sleep(0.5) # Simulate 0.5s AI latency
            return "Narrativa gerada"
        ai_handler.gerar_narrativa_combate.side_effect = delayed_narrative

        bot.get_cog.return_value = ai_handler

        combat_cog = Combat(bot)

        # Mock Session
        channel_id = 123
        combat_cog.sessions[channel_id] = {
            'status': 'RODANDO',
            'bloqueado': False,
            'mensagem_id': 999,
            'regiao': 'Teste',
            'monstros': [{'id': 1, 'nome': 'Goblin', 'hp_atual': 20, 'hp_max': 20, 'dano_base': '1d6'}],
            'jogadores': [{'user_id': 456, 'nome': 'Hero', 'hp': 20, 'hp_max': 20, 'atk': 5}],
            'ordem': [{'user_id': 456, 'tipo': 'JOGADOR', 'nome': 'Hero'}],
            'turno_index': 0,
            'log': [],
            'round': 1,
            'battlemap_enviado': True,
            'status_effects': {}
        }

        # Mock Interaction
        interaction = AsyncMock()
        interaction.channel_id = channel_id
        interaction.user.id = 456
        interaction.user.display_name = "Hero"
        interaction.channel = AsyncMock()
        interaction.channel.id = channel_id

        # Mock internal methods to avoid side effects
        combat_cog.avancar_indice_turno = AsyncMock()
        combat_cog.atualizar_interface = AsyncMock()
        combat_cog._atualizar_economia_regional = AsyncMock()

        # Measure time
        start_time = time.time()

        # Run action
        await combat_cog.processar_acao_jogador(interaction, channel_id, "Ataque Básico")

        end_time = time.time()
        duration = end_time - start_time

        print(f"Execution time: {duration:.4f}s")
        self.assertLess(duration, 0.1, "Non-blocking AI should take less than 0.1s")

        # Verify that background task was created and is running/pending
        # We can wait for a bit and check if log was updated (since we mocked ai_handler to take 0.5s)
        self.assertEqual(len(combat_cog.sessions[channel_id]['log']), 1) # Only basic log

        # Now wait for pending tasks
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending)

        # After waiting, the log should have the AI narrative
        self.assertEqual(len(combat_cog.sessions[channel_id]['log']), 2)
        self.assertIn("Narrativa gerada", combat_cog.sessions[channel_id]['log'][1])

if __name__ == "__main__":
    unittest.main()
