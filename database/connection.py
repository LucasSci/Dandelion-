from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

DB_NAME = "bestiario.db"
BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_db_path(db_path: Union[str, Path]) -> Path:
    path = Path(db_path)
    return path if path.is_absolute() else BASE_DIR / path


def get_connection(db_path: Union[str, Path] = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
