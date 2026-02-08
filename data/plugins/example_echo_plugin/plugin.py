from __future__ import annotations

from typing import Dict


def handle_narration(payload: Dict[str, str]) -> Dict[str, str]:
    prompt = payload.get("prompt", "")
    return {"response": f"[Echo] {prompt}"}
