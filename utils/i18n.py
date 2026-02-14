from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from babel.dates import format_date as babel_format_date
from babel.dates import format_datetime as babel_format_datetime
from babel.numbers import format_currency as babel_format_currency
from zoneinfo import ZoneInfo

from config import settings

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")


@dataclass(frozen=True)
class I18nContext:
    locale: str
    timezone: str
    currency: str

    def t(self, key: str, **kwargs: Any) -> str:
        return translate(key, locale=self.locale, **kwargs)

    def format_datetime(self, value, format: str = "medium") -> str:
        return format_datetime(value, locale=self.locale, timezone=self.timezone, format=format)

    def format_date(self, value, format: str = "medium") -> str:
        return format_date(value, locale=self.locale, timezone=self.timezone, format=format)

    def format_currency(self, amount: float | int) -> str:
        return format_currency(amount, currency=self.currency, locale=self.locale)


@lru_cache(maxsize=None)
def _available_locales() -> set[str]:
    if not os.path.isdir(LOCALES_DIR):
        return set()
    return {
        filename.replace(".json", "")
        for filename in os.listdir(LOCALES_DIR)
        if filename.endswith(".json")
    }


def normalize_locale(locale: str) -> str:
    # Babel expects underscores for locales (e.g. pt_BR), but many web standards use dashes (pt-BR)
    # We normalize to underscore for Babel compatibility where needed, but this function
    # seems to have been returning dash-separated.
    # However, babel functions often handle both if parsed correctly, but Locale.parse specifically wants underscores or correct separation.

    # Existing logic returned dash separated (e.g. 'pt-BR').
    # If Babel fails with 'pt-BR', we might need to change how we pass it to Babel functions
    # OR change this normalization to use underscores.
    # Given the codebase uses this for filename lookups (json files), changing to underscore might break file lookups if files are named 'pt-BR.json'.

    # Let's keep the return format as dash-separated for internal consistency (file lookups),
    # but Ensure we replace dashes with underscores ONLY when passing to Babel functions in format_* wrappers.

    locale = locale.replace("_", "-")
    parts = locale.split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}-{parts[1].upper()}"


def resolve_locale(locale: str | None) -> str:
    available = _available_locales()
    default_locale = normalize_locale(settings.default_locale)

    if not available:
        return default_locale

    if locale:
        normalized = normalize_locale(locale)
        if normalized in available:
            return normalized
        base = normalized.split("-")[0]
        for candidate in available:
            if candidate.split("-")[0] == base:
                return candidate

    for candidate in settings.priority_languages:
        candidate_norm = normalize_locale(candidate)
        if candidate_norm in available:
            return candidate_norm

    if default_locale in available:
        return default_locale

    return sorted(available)[0]


@lru_cache(maxsize=None)
def _load_locale(locale: str) -> dict[str, Any]:
    path = os.path.join(LOCALES_DIR, f"{locale}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _lookup_key(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def translate(key: str, locale: str | None = None, **kwargs: Any) -> str:
    chosen_locale = resolve_locale(locale)
    data = _load_locale(chosen_locale)
    value = _lookup_key(data, key)

    if value is None and chosen_locale != normalize_locale(settings.default_locale):
        fallback_data = _load_locale(normalize_locale(settings.default_locale))
        value = _lookup_key(fallback_data, key)

    if value is None:
        value = key

    if isinstance(value, str):
        return value.format(**kwargs)
    return str(value)


def parse_accept_language(header_value: str | None) -> list[str]:
    if not header_value:
        return []
    locales: list[tuple[str, float]] = []
    for part in header_value.split(","):
        item = part.strip()
        if not item:
            continue
        if ";" in item:
            locale, qvalue = item.split(";", 1)
            qvalue = qvalue.strip()
            q = 1.0
            if qvalue.startswith("q="):
                try:
                    q = float(qvalue[2:])
                except ValueError:
                    q = 1.0
            locales.append((locale.strip(), q))
        else:
            locales.append((item, 1.0))
    locales.sort(key=lambda item: item[1], reverse=True)
    return [locale for locale, _ in locales]


def resolve_locale_from_accept_language(header_value: str | None) -> str:
    for locale in parse_accept_language(header_value):
        resolved = resolve_locale(locale)
        if resolved:
            return resolved
    return resolve_locale(None)


def get_interaction_locale(interaction) -> str:
    locale = getattr(interaction, "locale", None) or getattr(interaction, "guild_locale", None)
    locale_str = str(locale) if locale else None
    return resolve_locale(locale_str)


def get_request_locale(request) -> str:
    header_value = request.headers.get("accept-language") if request else None
    return resolve_locale_from_accept_language(header_value)


def get_default_timezone() -> str:
    return settings.default_timezone


def get_default_currency() -> str:
    return settings.default_currency


def get_interaction_context(interaction) -> I18nContext:
    return I18nContext(
        locale=get_interaction_locale(interaction),
        timezone=settings.default_timezone,
        currency=settings.default_currency,
    )


def format_datetime(value, locale: str | None = None, timezone: str | None = None, format: str = "medium") -> str:
    chosen_locale = resolve_locale(locale).replace("-", "_")
    tz = timezone or settings.default_timezone
    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = ZoneInfo("UTC")
    return babel_format_datetime(value, format=format, tzinfo=tzinfo, locale=chosen_locale)


def format_date(value, locale: str | None = None, timezone: str | None = None, format: str = "medium") -> str:
    chosen_locale = resolve_locale(locale).replace("-", "_")
    tz = timezone or settings.default_timezone
    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = ZoneInfo("UTC")
    return babel_format_date(value, format=format, locale=chosen_locale, tzinfo=tzinfo)


def format_currency(amount: float | int, currency: str | None = None, locale: str | None = None) -> str:
    chosen_locale = resolve_locale(locale).replace("-", "_")
    currency_code = currency or settings.default_currency
    return babel_format_currency(amount, currency_code, locale=chosen_locale)

