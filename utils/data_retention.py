from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from config import settings


ARCHIVE_TABLES = (
    "session_logs_archive",
    "memoria_campanha_archive",
    "mencoes_personagem_archive",
)


async def ensure_archive_tables(db) -> None:
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS session_logs_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            channel_id INTEGER,
            user_name TEXT,
            content TEXT,
            is_bot BOOLEAN,
            timestamp TEXT,
            archived_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS memoria_campanha_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            tipo TEXT,
            conteudo TEXT,
            data_registro TEXT,
            archived_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS mencoes_personagem_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            personagem_id INTEGER,
            session_log_id INTEGER,
            memoria_id INTEGER,
            descricao_fato TEXT,
            relevancia INTEGER,
            criado_em TEXT,
            archived_at TEXT DEFAULT (datetime('now'))
        );
        """
    )


async def archive_and_purge(db, logger: logging.Logger) -> None:
    await ensure_archive_tables(db)

    retention_logs = settings.retention_days_session_logs
    retention_memoria = settings.retention_days_memoria_campanha
    retention_mencoes = settings.retention_days_mencoes_personagem
    archive_after_days = settings.archive_after_days

    if settings.archive_enabled:
        await db.execute(
            """
            INSERT INTO session_logs_archive
                (original_id, channel_id, user_name, content, is_bot, timestamp)
            SELECT id, channel_id, user_name, content, is_bot, timestamp
            FROM session_logs
            WHERE timestamp < datetime('now', ?)
            """,
            (f"-{archive_after_days} days",),
        )
        await db.execute(
            """
            INSERT INTO memoria_campanha_archive
                (original_id, tipo, conteudo, data_registro)
            SELECT id, tipo, conteudo, data_registro
            FROM memoria_campanha
            WHERE data_registro < datetime('now', ?)
            """,
            (f"-{archive_after_days} days",),
        )
        await db.execute(
            """
            INSERT INTO mencoes_personagem_archive
                (original_id, personagem_id, session_log_id, memoria_id, descricao_fato, relevancia, criado_em)
            SELECT id, personagem_id, session_log_id, memoria_id, descricao_fato, relevancia, criado_em
            FROM mencoes_personagem
            WHERE criado_em < datetime('now', ?)
            """,
            (f"-{archive_after_days} days",),
        )

        await db.execute(
            "DELETE FROM session_logs WHERE timestamp < datetime('now', ?)",
            (f"-{archive_after_days} days",),
        )
        await db.execute(
            "DELETE FROM memoria_campanha WHERE data_registro < datetime('now', ?)",
            (f"-{archive_after_days} days",),
        )
        await db.execute(
            "DELETE FROM mencoes_personagem WHERE criado_em < datetime('now', ?)",
            (f"-{archive_after_days} days",),
        )

    await db.execute(
        "DELETE FROM session_logs WHERE timestamp < datetime('now', ?)",
        (f"-{retention_logs} days",),
    )
    await db.execute(
        "DELETE FROM memoria_campanha WHERE data_registro < datetime('now', ?)",
        (f"-{retention_memoria} days",),
    )
    await db.execute(
        "DELETE FROM mencoes_personagem WHERE criado_em < datetime('now', ?)",
        (f"-{retention_mencoes} days",),
    )
    await db.commit()
    logger.info(
        "Retenção aplicada (logs=%s dias, memoria=%s dias, mencoes=%s dias, archive=%s dias, enabled=%s).",
        retention_logs,
        retention_memoria,
        retention_mencoes,
        archive_after_days,
        settings.archive_enabled,
    )


async def start_retention_loop(db, logger: logging.Logger, interval_hours: int = 12) -> asyncio.Task:
    async def _loop() -> None:
        while True:
            try:
                await archive_and_purge(db, logger)
            except Exception:
                logger.exception("Falha ao aplicar políticas de retenção.")
            await asyncio.sleep(interval_hours * 3600)

    return asyncio.create_task(_loop(), name="data-retention-loop")


async def stop_retention_loop(task: asyncio.Task | None) -> None:
    if not task:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
