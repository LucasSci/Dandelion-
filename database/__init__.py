from __future__ import annotations

from pathlib import Path
from typing import Union

from .connection import DB_NAME, BASE_DIR, get_connection
from .migrations import migrate_db
from .seeds import (
    SEEDS_DIR,
    SEED_LOCATIONS_SQL,
    SEED_LOOKUPS_SQL,
    SEED_MONSTERS_SQL,
    SEED_RELATIONS_SQL,
    seed_bestiary,
)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _load_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def init_db(db_path: Union[str, Path] = DB_NAME) -> None:
    db_path = Path(db_path)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        cur = conn.cursor()

        # 1) Schema (Cria todas as tabelas)
        cur.executescript(_load_schema())

        # 2) Migrações (Atualiza tabelas antigas se necessário)
        migrate_db(cur)

        conn.commit()

        # 3) Seeds (Popula dados iniciais)
        seed_bestiary(conn)


__all__ = [
    "DB_NAME",
    "BASE_DIR",
    "SEEDS_DIR",
    "SEED_LOCATIONS_SQL",
    "SEED_LOOKUPS_SQL",
    "SEED_MONSTERS_SQL",
    "SEED_RELATIONS_SQL",
    "get_connection",
    "init_db",
]
