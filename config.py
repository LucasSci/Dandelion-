import os
from dataclasses import dataclass
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_token: Optional[str]
    gemini_api_key: Optional[str]
    extensions: Tuple[str, ...]
    optional_extensions: Tuple[str, ...]


def load_settings() -> Settings:
    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        extensions=(
            "cogs.ai_handler",
            "cogs.bestiary",
            "cogs.combat",
            "cogs.scribe",
            "cogs.quests",
            "cogs.campaign",
        ),
        optional_extensions=("cogs.shop",),
    )


settings = load_settings()
