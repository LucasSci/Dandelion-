from __future__ import annotations

import re
from typing import Iterable

_TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")


def resolve_roll_template(formula: str, attributes: dict[str, int]) -> tuple[str, list[str]]:
    if not formula:
        return "", []

    normalized = {str(key).strip().upper(): value for key, value in attributes.items()}
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        key = token.upper()
        if key not in normalized:
            missing.append(token)
            return match.group(0)
        return str(normalized[key])

    resolved = _TOKEN_PATTERN.sub(_replace, formula)
    return resolved, missing
