import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Optional

DB_NAME = "bestiario.db"


# =========================
# CONEXAO / UTIL
# =========================

def get_connection(db_path: str = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cursor.fetchall())


def _add_columns_if_missing(
    cursor: sqlite3.Cursor,
    table: str,
    columns: Iterable[Tuple[str, str]],
) -> None:
    for col, col_type in columns:
        if not _column_exists(cursor, table, col):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    )
    return cursor.fetchone() is not None


# =========================
# SCHEMA (TABELAS)
# =========================

SCHEMA_SQL = """
-- =========================
-- TABELAS RPG (LEGADO)
-- =========================

CREATE TABLE IF NOT EXISTS personagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    nome TEXT UNIQUE,
    raca TEXT,
    classe TEXT,
    nivel INTEGER DEFAULT 1,
    xp_atual INTEGER DEFAULT 0,
    historia TEXT,
    imagem_url TEXT,
    ouro INTEGER DEFAULT 0,
    hp_max INTEGER DEFAULT 30,
    mp_max INTEGER DEFAULT 10,
    ataque INTEGER DEFAULT 2,
    defesa INTEGER DEFAULT 10
);

CREATE TABLE IF NOT EXISTS criaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE,
    descricao TEXT,
    fraquezas TEXT,
    imagem_url TEXT,
    hp_max INTEGER DEFAULT 50,
    iniciativa INTEGER DEFAULT 10,
    dano_base TEXT DEFAULT '1d6'
);

CREATE TABLE IF NOT EXISTS habilidades_personagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personagem_id INTEGER,
    nome TEXT,
    descricao TEXT,
    dado TEXT,
    FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    nome TEXT,
    tipo TEXT,
    valor INTEGER,
    efeito TEXT
);

-- =========================
-- BESTIARIO (NORMALIZADO)
-- =========================

CREATE TABLE IF NOT EXISTS monsters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  threat_level INTEGER DEFAULT 1,
  description TEXT,
  behavior TEXT,
  habitat TEXT,
  signs TEXT,
  notes TEXT,
  origin TEXT,                      -- ex: books, tw1, tw2, tw3, hos, baw, gwent, thronebreaker, comics, original
  canon_tier TEXT DEFAULT 'core',    -- core/extended/apocrypha
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monster_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weaknesses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  key TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_weaknesses (
  monster_id INTEGER NOT NULL,
  weakness_id INTEGER NOT NULL,
  priority INTEGER DEFAULT 2,
  note TEXT,
  PRIMARY KEY (monster_id, weakness_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (weakness_id) REFERENCES weaknesses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS traits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_traits (
  monster_id INTEGER NOT NULL,
  trait_id INTEGER NOT NULL,
  PRIMARY KEY (monster_id, trait_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (trait_id) REFERENCES traits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS loot_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_loot (
  monster_id INTEGER NOT NULL,
  loot_item_id INTEGER NOT NULL,
  rarity INTEGER DEFAULT 2,
  note TEXT,
  PRIMARY KEY (monster_id, loot_item_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (loot_item_id) REFERENCES loot_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monster_id INTEGER NOT NULL,
  file_path TEXT,
  prompt TEXT,
  model TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE
);

-- =========================
-- SOURCES (ECOSSISTEMA)
-- =========================

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,     -- books, tw1, tw2, tw3, hos, baw, gwent, thronebreaker, comics, original
  label TEXT NOT NULL,
  canon_tier TEXT NOT NULL      -- core/extended/apocrypha
);

CREATE TABLE IF NOT EXISTS monster_sources (
  monster_id INTEGER NOT NULL,
  source_id INTEGER NOT NULL,
  PRIMARY KEY (monster_id, source_id),
  FOREIGN KEY(monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- =========================
-- INDICES
-- =========================

CREATE INDEX IF NOT EXISTS idx_personagens_user_id ON personagens(user_id);
CREATE INDEX IF NOT EXISTS idx_inventario_user_id ON inventario(user_id);
CREATE INDEX IF NOT EXISTS idx_habilidades_personagem_id ON habilidades_personagem(personagem_id);
CREATE INDEX IF NOT EXISTS idx_criaturas_nome ON criaturas(nome);

CREATE INDEX IF NOT EXISTS idx_monsters_category ON monsters(category);
CREATE INDEX IF NOT EXISTS idx_monsters_name ON monsters(name);
CREATE INDEX IF NOT EXISTS idx_weaknesses_type ON weaknesses(type);
CREATE INDEX IF NOT EXISTS idx_traits_key ON traits(key);
CREATE INDEX IF NOT EXISTS idx_loot_items_key ON loot_items(key);
CREATE INDEX IF NOT EXISTS idx_sources_key ON sources(key);
"""


# =========================
# MIGRACOES
# =========================

def migrate_legacy_personagens(cursor: sqlite3.Cursor) -> None:
    columns_extras = [
        ("hp_max", "INTEGER DEFAULT 30"),
        ("mp_max", "INTEGER DEFAULT 10"),
        ("ataque", "INTEGER DEFAULT 2"),
        ("defesa", "INTEGER DEFAULT 10"),
        ("xp_atual", "INTEGER DEFAULT 0"),
    ]
    if _table_exists(cursor, "personagens"):
        _add_columns_if_missing(cursor, "personagens", columns_extras)


def migrate_monsters_columns(cursor: sqlite3.Cursor) -> None:
    # caso alguém já tenha um DB antigo onde monsters existe sem origin/canon_tier
    columns_extras = [
        ("origin", "TEXT"),
        ("canon_tier", "TEXT DEFAULT 'core'"),
    ]
    if _table_exists(cursor, "monsters"):
        _add_columns_if_missing(cursor, "monsters", columns_extras)


# =========================
# SEEDS
# =========================

SEED_LOOKUPS_SQL = """
-- Weaknesses
INSERT OR IGNORE INTO weaknesses (type, key, label) VALUES
('oil','necrophage_oil','Óleo contra Necrófagos'),
('oil','specter_oil','Óleo contra Espectros'),
('oil','hanged_mans_venom','Veneno do Enforcado'),

('bomb','samum','Samum'),
('bomb','grapeshot','Bomba de Pólvora'),
('bomb','dancing_star','Estrela Dançante'),
('bomb','devils_puffball','Sopro do Diabo'),
('bomb','moon_dust','Pó da Lua'),
('bomb','northern_wind','Vento do Norte'),

('sign','igni','Igni'),
('sign','yrden','Yrden'),
('sign','aard','Aard'),
('sign','quen','Quen'),
('sign','axii','Axii'),

('misc','fire','Fogo'),
('misc','silver','Prata'),
('misc','keep_distance','Manter distância / controlar alcance');

-- Traits
INSERT OR IGNORE INTO traits (key, label) VALUES
('pack_hunter','Caça em bando'),
('nocturnal','Noturno'),
('carrion_feeder','Alimenta-se de carniça'),
('ambusher','Emboscador'),
('regenerative','Regenerativo'),
('poisonous','Venenoso'),
('waterbound','Vinculado à água'),
('disease_risk','Risco de praga/doença'),
('territorial','Territorial');

-- Loot (genérico, você ajusta depois)
INSERT OR IGNORE INTO loot_items (key, label) VALUES
('monster_claw','Garra de monstro'),
('monster_tooth','Dente de monstro'),
('rotting_flesh','Carne putrefata'),
('monster_blood','Sangue de monstro'),
('mutagen_minor','Mutágeno menor'),
('essence_necrophage','Essência de necrófago');

-- Sources (ecossistema)
INSERT OR IGNORE INTO sources (key,label,canon_tier) VALUES
('books','Livros (Sapkowski)','core'),
('tw1','The Witcher 1','core'),
('tw2','The Witcher 2','core'),
('tw3','The Witcher 3','core'),
('hos','Hearts of Stone','core'),
('baw','Blood and Wine','core'),
('thronebreaker','Thronebreaker','extended'),
('gwent','Gwent','extended'),
('comics','Quadrinhos licenciados','extended'),
('original','Originais (Witcher-like)','apocrypha');
"""

# Importante: aqui só vai "base canônica mínima" para validar pipeline.
# Você vai ampliar isso em lotes por arquivo SQL, ou por script de import depois.
SEED_MONSTERS_SQL = """
-- ================
-- NECROPHAGE (TW3) - mínimo
-- ================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('drowner','Drowner','Necrophage',2,'tw3','core'),
('water_hag','Water Hag','Necrophage',3,'tw3','core'),
('ghoul','Ghoul','Necrophage',2,'tw3','core'),
('alghoul','Alghoul','Necrophage',4,'tw3','core'),
('rotfiend','Rotfiend','Necrophage',3,'tw3','core');

-- ================
-- SPECTER (TW3) - mínimo
-- ================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('wraith','Wraith','Specter',3,'tw3','core'),
('nightwraith','Nightwraith','Specter',3,'tw3','core'),
('noonwraith','Noonwraith','Specter',3,'tw3','core');
"""

SEED_RELATIONS_SQL = """
-- Liga monsters (que já têm origin preenchido) ao sources equivalentes
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = m.origin
WHERE m.origin IS NOT NULL AND m.origin <> '';

-- Fraquezas padrão para Specters (ajuste depois se quiser granularidade)
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão para espectros.'
FROM monsters m, weaknesses w
WHERE m.category='Specter' AND w.key IN ('specter_oil','yrden','moon_dust');

-- Fraquezas padrão para Necrophages
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão para necrófagos.'
FROM monsters m, weaknesses w
WHERE m.category='Necrophage' AND w.key IN ('necrophage_oil','igni','aard','quen','silver');


"""
from pathlib import Path


def seed_bestiary(conn: sqlite3.Connection) -> None:
    
    from pathlib import Path
    for file in [
        "seed_bestiary_ecosystem.sql",
        "seed_tw3_full_by_category.sql",
        "seed_books_core.sql",
        "seed_books_core_lote2.sql",
        "seed_tw2_full.sql",
        "seed_dlcs_hos_baw.sql"
    ]:
        conn.executescript(Path(file).read_text(encoding="utf-8"))

    conn.commit()
    sql = Path("seed_bestiary_ecosystem.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    cur = conn.cursor()
    cur.executescript(SEED_LOOKUPS_SQL)
    cur.executescript(SEED_MONSTERS_SQL)
    cur.executescript(SEED_RELATIONS_SQL)
    conn.commit()


# =========================
# LIMPEZA OPCIONAL (SE VOCE JÁ TINHA DADOS "AUTORAIS")
# =========================

def mark_unknown_slugs_as_apocrypha(conn: sqlite3.Connection, known_slugs: Iterable[str]) -> int:
    """
    Se você rodou seeds anteriores com slugs autorais, use isso para marcar o que NÃO estiver
    na sua lista canônica atual como apocrypha/original (sem deletar).
    """
    known = set(known_slugs)
    cur = conn.cursor()
    cur.execute("SELECT slug FROM monsters;")
    all_slugs = [r[0] for r in cur.fetchall()]

    to_mark = [s for s in all_slugs if s not in known]
    if not to_mark:
        return 0

    cur.executemany(
        "UPDATE monsters SET canon_tier='apocrypha', origin='original' WHERE slug=?;",
        [(s,) for s in to_mark],
    )
    conn.commit()
    return len(to_mark)


# =========================
# INIT
# =========================

def init_db(db_path: str = DB_NAME) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        cur = conn.cursor()

        # 1) schema
        cur.executescript(SCHEMA_SQL)

        # 2) migrações idempotentes
        migrate_legacy_personagens(cur)
        migrate_monsters_columns(cur)

        conn.commit()

        # 3) seeds idempotentes
        seed_bestiary(conn)


if __name__ == "__main__":
    init_db(DB_NAME)
    print(f"✅ Banco inicializado e seeds aplicados: {DB_NAME}")
