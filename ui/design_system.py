from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

import discord
from discord import ui


@dataclass(frozen=True)
class DesignTokens:
    colors: Mapping[str, int]
    emojis: Mapping[str, str]
    spacing: Mapping[str, int]


@dataclass(frozen=True)
class Theme:
    name: str
    description: str
    tokens: DesignTokens


DEFAULT_TOKENS = DesignTokens(
    colors={
        "brand": 0x6D28D9,
        "surface": 0x2B2D31,
        "accent": 0x16A34A,
        "warning": 0xF59E0B,
        "danger": 0xDC2626,
        "info": 0x2563EB,
        "muted": 0x475569,
    },
    emojis={
        "spark": "✨",
        "compass": "🧭",
        "dashboard": "📊",
        "onboarding": "🚀",
        "check": "✅",
        "alert": "⚠️",
    },
    spacing={
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
    },
)


DEFAULT_THEME = Theme(
    name="Witcher Noir",
    description="Tema escuro com acentos vibrantes e contraste alto.",
    tokens=DEFAULT_TOKENS,
)


def themed_embed(
    title: str,
    description: Optional[str] = None,
    *,
    variant: str = "surface",
) -> discord.Embed:
    color = DEFAULT_THEME.tokens.colors.get(variant, DEFAULT_THEME.tokens.colors["brand"])
    return discord.Embed(title=title, description=description, color=color)


def apply_navigation_state(
    view: ui.View,
    active_key: str,
    label_to_key: Mapping[str, str],
    *,
    active_style: discord.ButtonStyle = discord.ButtonStyle.primary,
    inactive_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
) -> None:
    for item in view.children:
        if not isinstance(item, ui.Button) or not item.label:
            continue
        key = label_to_key.get(item.label)
        if not key:
            continue
        is_active = key == active_key
        item.disabled = is_active
        item.style = active_style if is_active else inactive_style


def build_section_lines(title: str, lines: Iterable[str]) -> str:
    safe_lines = [line for line in lines if line]
    if not safe_lines:
        return f"**{title}**\n—"
    return f"**{title}**\n" + "\n".join(safe_lines)
