import unittest
import asyncio
import discord
from ui.guide_view import GuideView

class TestGuideView(unittest.IsolatedAsyncioTestCase):
    async def test_instantiation(self):
        view = GuideView()
        self.assertIsInstance(view, discord.ui.View)
        self.assertEqual(len(view.children), 1)

    async def test_get_embed_home(self):
        view = GuideView()
        embed = view.get_embed("home")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Bem-vindo", embed.title)

    async def test_get_embed_players(self):
        view = GuideView()
        embed = view.get_embed("players")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Jogadores", embed.title)

    async def test_get_embed_gms(self):
        view = GuideView()
        embed = view.get_embed("gms")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Mestres", embed.title)

if __name__ == '__main__':
    unittest.main()
