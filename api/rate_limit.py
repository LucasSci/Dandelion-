from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Depends, HTTPException, Request

from api.auth import require_api_key

RATE_LIMIT = int(os.getenv("DANDELION_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("DANDELION_RATE_LIMIT_WINDOW", "60"))

_rate_limit_store: defaultdict[str, Deque[float]] = defaultdict(deque)


def _prune(entries: Deque[float], now: float) -> None:
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    while entries and entries[0] < window_start:
        entries.popleft()


async def rate_limiter(
    request: Request,
    api_key: str = Depends(require_api_key),
) -> None:
    now = time.monotonic()
    key = f"{api_key}:{request.url.path}"
    entries = _rate_limit_store[key]
    _prune(entries, now)
    if len(entries) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "Rate limit exceeded. "
                f"Max {RATE_LIMIT} requests per {RATE_LIMIT_WINDOW_SECONDS}s."
            ),
        )
    entries.append(now)
