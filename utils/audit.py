from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from utils.crypto import encrypt_sensitive_data

DEFAULT_AUDIT_LOG_PATH = "data/audit.log"


def _audit_log_path() -> str:
    return os.getenv("AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH)


def log_audit_event(event: dict[str, Any], encrypt_fields: Iterable[str] | None = None) -> None:
    event = dict(event)
    event.setdefault("event_id", str(uuid4()))
    event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    if encrypt_fields:
        for field in encrypt_fields:
            if field in event and event[field] is not None:
                event[field] = encrypt_sensitive_data(str(event[field]))
    path = _audit_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
