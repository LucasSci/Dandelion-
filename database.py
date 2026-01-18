import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Optional
import logging

# Configuração básica de log para ver o que está acontecendo no console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = "bestiario.db"

# =========================
# CONEXAO / UTIL
# =========================

def get_connection(db_path: str = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    try:
        cursor.execute(f"PRAGMA table_info({table});")
        return any(row[1] == column for row in cursor.fetchall())
    except Exception:
        return False

def _add_columns_if_missing(cursor: sqlite3.Cursor, table: str, columns: Iterable[Tuple[str, str]]) -> None:
    if not _table_exists(cursor, table):
        return

    for col, col_type in columns:
        if not _column_exists(cursor, table, col):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
                logger.info(f"🔧 Coluna '{col}' adicionada em '{table}'.")
            except Exception as e:
                logger.error(f"⚠️ Erro ao adicionar coluna {col} em {table}: {e}")

def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cursor.fetchone() is not None

# =========================
# SCHEMA (APENAS CRIAÇÃO)
# =========================
# Removi os ALTER TABLE daqui. Eles vão para a migração.
# Consolidei a tabela quests.

SCHEMA_SQL = """
-- NOVA TABELA: Pontos de Interesse (Cidades, Ruínas, etc)
CREATE TABLE IF NOT EXISTS locais_mundo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE,
    regiao TEXT,
    descricao_lore TEXT,
    lendas_locais TEXT,
    coord_x INTEGER,
    coord_y INTEGER,
    nivel_perigo INTEGER DEFAULT 1
);

-- CORE RPG --
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
    hp_atual INTEGER DEFAULT 30,
    mp_max INTEGER DEFAULT 10,
    ataque INTEGER DEFAULT 2,
    defesa INTEGER DEFAULT 10,
    -- Campos de Localização (Já incluídos na criação para novos bancos)
    localizacao_atual TEXT DEFAULT 'Deserto de Korath',
    coord_x INTEGER DEFAULT 0,
    coord_y INTEGER DEFAULT 0
);

-- QUESTS UNIFICADA --
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    descricao TEXT,
    recompensa_ouro INTEGER DEFAULT 0,
    recompensa_xp INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Disponivel',
    regiao TEXT DEFAULT 'Desconhecida',
    max_jogadores INTEGER DEFAULT 1,
    thread_id INTEGER,
    classes_req TEXT DEFAULT 'Todas',
    criatura_id INTEGER,
    alvo_monstro_nome TEXT,
    imagem_url TEXT,
    alvo_monstro TEXT, 
    -- Novos Campos de Mapa
    coord_x INTEGER DEFAULT 0,
    coord_y INTEGER DEFAULT 0,
    local_nome TEXT DEFAULT 'Desconhecido'
);

CREATE TABLE IF NOT EXISTS quest_participantes (
    quest_id INTEGER, 
    user_id INTEGER, 
    FOREIGN KEY(quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    PRIMARY KEY(quest_id, user_id)
);

CREATE TABLE IF NOT EXISTS memoria_campanha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    conteudo TEXT,
    data_registro TEXT DEFAULT (datetime('now'))
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

CREATE TABLE IF NOT EXISTS session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    user_name TEXT,
    content TEXT,
    is_bot BOOLEAN,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loja_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT,
    preco INTEGER DEFAULT 0,
    estoque INTEGER DEFAULT 1,
    efeito TEXT,
    descricao TEXT
);

-- BESTIÁRIO (SIMPLIFICADO - Mantido para compatibilidade legado se necessário)
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

-- BESTIÁRIO NORMALIZADO --
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
  origin TEXT,                      
  canon_tier TEXT DEFAULT 'core',    
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

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  canon_tier TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_sources (
  monster_id INTEGER NOT NULL,
  source_id INTEGER NOT NULL,
  PRIMARY KEY (monster_id, source_id),
  FOREIGN KEY(monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- INDICES
CREATE INDEX IF NOT EXISTS idx_personagens_user_id ON personagens(user_id);
CREATE INDEX IF NOT EXISTS idx_inventario_user_id ON inventario(user_id);
CREATE INDEX IF NOT EXISTS idx_habilidades_personagem_id ON habilidades_personagem(personagem_id);
CREATE INDEX IF NOT EXISTS idx_criaturas_nome ON criaturas(nome);
CREATE INDEX IF NOT EXISTS idx_monsters_category ON monsters(category);
"""

# =========================
# SEEDS
# =========================

SEED_LOOKUPS_SQL = """
INSERT OR IGNORE INTO weaknesses (type, key, label) VALUES
('oil','necrophage_oil','Óleo contra Necrófagos'),
('oil','specter_oil','Óleo contra Espectros'),
('oil','hanged_mans_venom','Veneno do Enforcado'),
('bomb','samum','Samum'),
('bomb','grapeshot','Bomba de Pólvora'),
('bomb','moon_dust','Pó da Lua'),
('sign','igni','Igni'),
('sign','yrden','Yrden'),
('sign','aard','Aard'),
('sign','quen','Quen'),
('sign','axii','Axii'),
('misc','silver','Prata');

INSERT OR IGNORE INTO traits (key, label) VALUES
('pack_hunter','Caça em bando'),
('nocturnal','Noturno'),
('regenerative','Regenerativo');

INSERT OR IGNORE INTO sources (key,label,canon_tier) VALUES
('tw3','The Witcher 3','core'),
('books','Livros','core');
"""

SEED_MONSTERS_SQL = """
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('drowner','Drowner','Necrophage',2,'tw3','core'),
('ghoul','Ghoul','Necrophage',2,'tw3','core'),
('wraith','Wraith','Specter',3,'tw3','core');
"""

SEED_RELATIONS_SQL = """
-- Relacionar monstros com sources e fraquezas de forma segura
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id FROM monsters m JOIN sources s ON s.key = m.origin
WHERE m.origin IS NOT NULL;
"""

# =========================
# MIGRACOES
# =========================

def migrate_db(cursor: sqlite3.Cursor) -> None:
    """Centraliza todas as migrações (ALTER TABLES seguros)."""
    
    # 1. Personagens: Atualizações de RPG e MAPA
    personagens_extras = [
        ("hp_max", "INTEGER DEFAULT 30"),
        ("mp_max", "INTEGER DEFAULT 10"),
        ("ataque", "INTEGER DEFAULT 2"),
        ("defesa", "INTEGER DEFAULT 10"),
        ("xp_atual", "INTEGER DEFAULT 0"),
        ("hp_atual", "INTEGER DEFAULT 30"),
        # Mapa
        ("localizacao_atual", "TEXT DEFAULT 'Deserto de Korath'"),
        ("coord_x", "INTEGER DEFAULT 0"),
        ("coord_y", "INTEGER DEFAULT 0")
    ]
    if _table_exists(cursor, "personagens"):
        _add_columns_if_missing(cursor, "personagens", personagens_extras)

    # 2. Quests: Atualizações de Mapa e Lógica
    quests_extras = [
        ("classes_req", "TEXT DEFAULT 'Todas'"),
        ("thread_id", "INTEGER"),
        ("regiao", "TEXT DEFAULT 'Desconhecida'"),
        ("max_jogadores", "INTEGER DEFAULT 1"),
        ("alvo_monstro", "TEXT"),
        ("criatura_id", "INTEGER"),
        ("alvo_monstro_nome", "TEXT"),
        ("imagem_url", "TEXT"),
        # Mapa
        ("coord_x", "INTEGER DEFAULT 0"),
        ("coord_y", "INTEGER DEFAULT 0"),
        ("local_nome", "TEXT DEFAULT 'Desconhecido'")
    ]
    if _table_exists(cursor, "quests"):
        _add_columns_if_missing(cursor, "quests", quests_extras)

    # 3. Monstros
    monsters_extras = [
        ("origin", "TEXT"),
        ("canon_tier", "TEXT DEFAULT 'core'"),
    ]
    if _table_exists(cursor, "monsters"):
        _add_columns_if_missing(cursor, "monsters", monsters_extras)

def seed_bestiary(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    
    # 1. Carregar arquivos SQL externos se existirem
    seed_files = [
        "seed_bestiary_ecosystem.sql",
        "seed_tw3_full_by_category.sql",
        "seed_books_core.sql"
    ]
    
    for filename in seed_files:
        p = Path(filename)
        if p.exists():
            try:
                logger.info(f"📄 Aplicando seed externo: {filename}")
                script = p.read_text(encoding="utf-8")
                conn.executescript(script)
                conn.commit()
            except Exception as e:
                logger.error(f"❌ Erro ao aplicar {filename}: {e}")

    # 2. Seeds internos de garantia
    try:
        cur.executescript(SEED_LOOKUPS_SQL)
        cur.executescript(SEED_MONSTERS_SQL)
        cur.executescript(SEED_RELATIONS_SQL)
        conn.commit()
    except Exception as e:
        logger.error(f"⚠️ Erro nos seeds internos: {e}")

# =========================
# INIT
# =========================

def init_db(db_path: str = DB_NAME) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        cur = conn.cursor()

        # 1) Schema (Cria todas as tabelas SE NÃO existirem)
        cur.executescript(SCHEMA_SQL)
        conn.commit()
        
        # 2) Migrações (Adiciona colunas novas em tabelas velhas)
        migrate_db(cur)
        conn.commit()

        # 3) Seeds (Popula dados iniciais)
        seed_bestiary(conn)

if __name__ == "__main__":
    init_db(DB_NAME)
    print(f"✅ Banco inicializado e verificado: {DB_NAME}")