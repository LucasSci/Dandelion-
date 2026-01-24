from __future__ import annotations

from typing import Mapping


def calculate_derived_stats(attributes: Mapping[str, int]) -> dict[str, int]:
    """Calcula os valores derivados com base nos atributos principais.

    Fórmulas documentadas para manter consistência:
    - Stun = BODY + WILL
    - Run = REF + DEX
    - Leap = BODY + DEX
    - Recovery = (BODY + WILL) // 2
    """

    def get_attr(name: str, default: int = 1) -> int:
        value = attributes.get(name, default)
        return int(value) if value is not None else default

    body = get_attr("BODY")
    will = get_attr("WILL")
    ref = get_attr("REF")
    dex = get_attr("DEX")

    return {
        "Stun": body + will,
        "Run": ref + dex,
        "Leap": body + dex,
        "Recovery": (body + will) // 2,
    }
