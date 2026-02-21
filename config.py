import os
from dataclasses import dataclass
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_token: Optional[str]
    gemini_api_key: Optional[str]
    roll20_campaign_url: Optional[str]
    vtt_api_url: Optional[str]
    default_character_thumbnail_url: Optional[str]
    log_level: str
    http_timeout_seconds: float
    retention_days_session_logs: int
    retention_days_memoria_campanha: int
    retention_days_mencoes_personagem: int
    archive_enabled: bool
    archive_after_days: int
    sync_commands: bool
    extensions: Tuple[str, ...]
    optional_extensions: Tuple[str, ...]
    default_locale: str
    default_timezone: str
    default_currency: str
    priority_languages: Tuple[str, ...]


def load_settings() -> Settings:
    sync_commands = os.getenv("SYNC_COMMANDS", "true").strip().lower() in {"1", "true", "yes", "on"}
    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        roll20_campaign_url=os.getenv("ROLL20_CAMPAIGN_URL"),
        vtt_api_url=os.getenv("VTT_API_URL"),
        default_character_thumbnail_url=os.getenv("DEFAULT_CHARACTER_THUMBNAIL_URL"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
        retention_days_session_logs=int(os.getenv("RETENTION_DAYS_SESSION_LOGS", "30")),
        retention_days_memoria_campanha=int(os.getenv("RETENTION_DAYS_MEMORIA_CAMPANHA", "180")),
        retention_days_mencoes_personagem=int(os.getenv("RETENTION_DAYS_MENCOES_PERSONAGEM", "180")),
        archive_enabled=os.getenv("ARCHIVE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
        archive_after_days=int(os.getenv("ARCHIVE_AFTER_DAYS", "90")),
        sync_commands=sync_commands,
        extensions=(
            "cogs.system",
            "cogs.experience",
            "cogs.ai_handler",
            "cogs.alchemy",
            "cogs.bestiary",
            "cogs.combat",
            "cogs.feedback_support",
            "cogs.command_tester",
            "cogs.scribe",
            "cogs.quests",
            "cogs.campaign",
            "cogs.roadmap",
            "cogs.rumors",
            "cogs.npcs",
            "cogs.progress",
            "cogs.gwent",
            "cogs.solo",
            "cogs.forum_session",
        ),
        optional_extensions=("cogs.shop",),
        default_locale=os.getenv("DEFAULT_LOCALE", "pt-BR"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "UTC"),
        default_currency=os.getenv("DEFAULT_CURRENCY", "BRL"),
        priority_languages=tuple(
            lang.strip()
            for lang in os.getenv("PRIORITY_LANGUAGES", "pt-BR,en-US,es-ES").split(",")
            if lang.strip()
        ),
    )


settings = load_settings()
