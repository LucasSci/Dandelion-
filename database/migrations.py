from __future__ import annotations

import sqlite3
from typing import Iterable, Tuple


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def _add_columns_if_missing(cursor: sqlite3.Cursor, table: str, columns: Iterable[Tuple[str, str]]) -> None:
    for col, col_type in columns:
        if not _column_exists(cursor, table, col):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
                print(f"🔧 Coluna '{col}' adicionada em '{table}'.")
            except Exception as e:
                print(f"⚠️ Erro ao adicionar coluna {col}: {e}")


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cursor.fetchone() is not None


def migrate_db(cursor: sqlite3.Cursor) -> None:
    """Centraliza todas as migrações"""

    # 1. Migração Personagens (HP Atual, MP, etc)
    personagens_extras = [
        ("titulo", "TEXT"),
        ("hp_max", "INTEGER DEFAULT 30"),
        ("mp_max", "INTEGER DEFAULT 10"),
        ("vigor_max", "INTEGER DEFAULT 10"),
        ("vigor_atual", "INTEGER DEFAULT 10"),
        ("toxicidade_max", "INTEGER DEFAULT 100"),
        ("toxicidade_atual", "INTEGER DEFAULT 0"),
        ("ataque", "INTEGER DEFAULT 2"),
        ("defesa", "INTEGER DEFAULT 10"),
        ("xp_atual", "INTEGER DEFAULT 0"),
        ("hp_atual", "INTEGER DEFAULT 30"),
        ("localizacao_id", "INTEGER"),
        ("genero", "TEXT"),
    ]
    if _table_exists(cursor, "personagens"):
        _add_columns_if_missing(cursor, "personagens", personagens_extras)

    world_location_extras = [
        ("biome", "TEXT"),
        ("clima", "TEXT"),
    ]
    if _table_exists(cursor, "world_locations"):
        _add_columns_if_missing(cursor, "world_locations", world_location_extras)

    # 2. Migração Monstros (Origin/Canon Tier)
    monsters_extras = [
        ("origin", "TEXT"),
        ("canon_tier", "TEXT DEFAULT 'core'"),
    ]
    if _table_exists(cursor, "monsters"):
        _add_columns_if_missing(cursor, "monsters", monsters_extras)

    criaturas_extras = [
        ("lore_cd", "INTEGER"),
    ]
    if _table_exists(cursor, "criaturas"):
        _add_columns_if_missing(cursor, "criaturas", criaturas_extras)

    lore_entries_extras = [
        ("is_private", "BOOLEAN DEFAULT 0"),
        ("owner_id", "INTEGER"),
    ]
    if _table_exists(cursor, "lore_entries"):
        _add_columns_if_missing(cursor, "lore_entries", lore_entries_extras)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lore_entries_owner_id ON lore_entries(owner_id);")

    # 3. Migração Quests (Restrição de Classe)
    quests_extras = [
        ("classes_req", "TEXT DEFAULT 'Todas'"),
        ("thread_id", "INTEGER"),
        ("regiao", "TEXT DEFAULT 'Desconhecida'"),
        ("max_jogadores", "INTEGER DEFAULT 1"),
        ("alvo_monstro", "TEXT"),
        ("nota_mestre", "TEXT"),
    ]
    if _table_exists(cursor, "quests"):
        _add_columns_if_missing(cursor, "quests", quests_extras)

    armaduras_extras = [
        ("reliability", "INTEGER DEFAULT 100"),
    ]
    if _table_exists(cursor, "armaduras_personagem"):
        _add_columns_if_missing(cursor, "armaduras_personagem", armaduras_extras)

    feedback_entries_extras = [
        ("user_id", "INTEGER"),
        ("guild_id", "INTEGER"),
        ("channel_id", "INTEGER"),
        ("feedback_type", "TEXT"),
        ("score", "INTEGER"),
        ("sentiment", "TEXT"),
        ("comentario", "TEXT"),
        ("contexto", "TEXT"),
        ("criado_em", "TEXT DEFAULT (datetime('now'))"),
    ]
    if _table_exists(cursor, "feedback_entries"):
        _add_columns_if_missing(cursor, "feedback_entries", feedback_entries_extras)

    support_tickets_extras = [
        ("user_id", "INTEGER"),
        ("guild_id", "INTEGER"),
        ("channel_id", "INTEGER"),
        ("titulo", "TEXT"),
        ("descricao", "TEXT"),
        ("categoria", "TEXT"),
        ("prioridade", "TEXT"),
        ("status", "TEXT DEFAULT 'Aberto'"),
        ("triagem_notas", "TEXT"),
        ("criado_em", "TEXT DEFAULT (datetime('now'))"),
        ("atualizado_em", "TEXT DEFAULT (datetime('now'))"),
    ]
    if _table_exists(cursor, "support_tickets"):
        _add_columns_if_missing(cursor, "support_tickets", support_tickets_extras)

    usage_events_extras = [
        ("user_id", "INTEGER"),
        ("guild_id", "INTEGER"),
        ("channel_id", "INTEGER"),
        ("command_name", "TEXT"),
        ("status", "TEXT"),
        ("criado_em", "TEXT DEFAULT (datetime('now'))"),
    ]
    if _table_exists(cursor, "usage_events"):
        _add_columns_if_missing(cursor, "usage_events", usage_events_extras)



    # 4. Migração de Índices de Performance
    try:
        # NOCASE para Autocomplete mais rápido (LIKE optimization)
        if _table_exists(cursor, "criaturas"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_criaturas_nome_nocase ON criaturas(nome COLLATE NOCASE);")
        if _table_exists(cursor, "monsters"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monsters_name_nocase ON monsters(name COLLATE NOCASE);")

        if _table_exists(cursor, "session_logs"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_logs_channel_id ON session_logs(channel_id);")
        if _table_exists(cursor, "quests"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quests_thread_id ON quests(thread_id);")
        print("⚡ Índices de performance aplicados.")
    except Exception as e:
        print(f"⚠️ Erro ao aplicar índices: {e}")

    if not _table_exists(cursor, "solo_campaigns"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solo_campaigns (
                user_id INTEGER PRIMARY KEY,
                personagem_id INTEGER NOT NULL,
                capitulo INTEGER DEFAULT 1,
                progresso INTEGER DEFAULT 0,
                gancho TEXT,
                ultima_localizacao_id INTEGER,
                ultima_acao_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE,
                FOREIGN KEY(ultima_localizacao_id) REFERENCES world_locations(id) ON DELETE SET NULL
            );
            """
        )

    if not _table_exists(cursor, "solo_story_entries"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solo_story_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                capitulo INTEGER DEFAULT 1,
                entrada TEXT NOT NULL,
                criado_em TEXT DEFAULT (datetime('now'))
            );
            """
        )

    if not _table_exists(cursor, "solo_resources"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solo_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                quantidade INTEGER DEFAULT 0,
                atualizado_em TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, nome)
            );
            """
        )

    if not _table_exists(cursor, "rolagens_personagem"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rolagens_personagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                formula TEXT NOT NULL,
                categoria TEXT,
                ordem INTEGER DEFAULT 0,
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
            );
            """
        )

    if not _table_exists(cursor, "alchemy_ingredients"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alchemy_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                tipo TEXT NOT NULL,
                biome TEXT,
                raridade INTEGER DEFAULT 1,
                qualidade_min INTEGER DEFAULT 40,
                qualidade_max INTEGER DEFAULT 100,
                descricao TEXT
            );
            """
        )

    if not _table_exists(cursor, "feedback_entries"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                feedback_type TEXT NOT NULL,
                score INTEGER,
                sentiment TEXT,
                comentario TEXT,
                contexto TEXT,
                criado_em TEXT DEFAULT (datetime('now'))
            );
            """
        )

    if not _table_exists(cursor, "support_tickets"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                titulo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT,
                prioridade TEXT,
                status TEXT DEFAULT 'Aberto',
                triagem_notas TEXT,
                criado_em TEXT DEFAULT (datetime('now')),
                atualizado_em TEXT DEFAULT (datetime('now'))
            );
            """
        )

    if not _table_exists(cursor, "usage_events"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                command_name TEXT NOT NULL,
                status TEXT NOT NULL,
                criado_em TEXT DEFAULT (datetime('now'))
            );
            """
        )

    if not _table_exists(cursor, "alchemy_recipes"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alchemy_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                base_alcoolica TEXT NOT NULL,
                efeito TEXT NOT NULL,
                toxicidade_base INTEGER DEFAULT 10,
                qualidade_min INTEGER DEFAULT 50
            );
            """
        )

    if not _table_exists(cursor, "alchemy_recipe_ingredients"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alchemy_recipe_ingredients (
                recipe_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantidade INTEGER DEFAULT 1,
                PRIMARY KEY (recipe_id, ingredient_id),
                FOREIGN KEY(recipe_id) REFERENCES alchemy_recipes(id) ON DELETE CASCADE,
                FOREIGN KEY(ingredient_id) REFERENCES alchemy_ingredients(id) ON DELETE CASCADE
            );
            """
        )

    if not _table_exists(cursor, "alchemy_user_ingredients"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alchemy_user_ingredients (
                user_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantidade INTEGER DEFAULT 0,
                qualidade INTEGER DEFAULT 0,
                atualizado_em TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, ingredient_id),
                FOREIGN KEY(ingredient_id) REFERENCES alchemy_ingredients(id) ON DELETE CASCADE
            );
            """
        )

    if not _table_exists(cursor, "alchemy_user_recipes"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alchemy_user_recipes (
                user_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                unlocked_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, recipe_id),
                FOREIGN KEY(recipe_id) REFERENCES alchemy_recipes(id) ON DELETE CASCADE
            );
            """
        )

    if not _table_exists(cursor, "personagem_memorias"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS personagem_memorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER NOT NULL,
                sessao_id INTEGER NOT NULL,
                criado_em TEXT DEFAULT (datetime('now')),
                UNIQUE(personagem_id, sessao_id),
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE,
                FOREIGN KEY(sessao_id) REFERENCES memoria_campanha(id) ON DELETE CASCADE
                log_id INTEGER,
                descricao_fato TEXT NOT NULL,
                relevancia INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE,
                FOREIGN KEY(log_id) REFERENCES session_logs(id) ON DELETE SET NULL
            );
            """
        )

    if _table_exists(cursor, "personagem_memorias"):
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_personagem_memorias_personagem_id ON personagem_memorias(personagem_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_personagem_memorias_sessao_id ON personagem_memorias(sessao_id);"
        )

    if not _table_exists(cursor, "transcription_settings"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transcription_settings (
                guild_id INTEGER PRIMARY KEY,
                transcription_channel_id INTEGER,
                summary_channel_id INTEGER
            );
            """
        )

    if not _table_exists(cursor, "mencoes_personagem"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mencoes_personagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER NOT NULL,
                session_log_id INTEGER,
                descricao_fato TEXT NOT NULL,
                relevancia INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE,
                FOREIGN KEY(session_log_id) REFERENCES session_logs(id) ON DELETE SET NULL
            );
            """
        )

    if _table_exists(cursor, "mencoes_personagem"):
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_mencoes_personagem_personagem_id ON mencoes_personagem(personagem_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_mencoes_personagem_session_log_id ON mencoes_personagem(session_log_id);"
        )

    if not _table_exists(cursor, "economia_regional"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS economia_regional (
                localizacao_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                modificador REAL DEFAULT 1.0,
                atualizado_em TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (localizacao_id, categoria),
                FOREIGN KEY(localizacao_id) REFERENCES world_locations(id) ON DELETE CASCADE
            );
            """
        )
