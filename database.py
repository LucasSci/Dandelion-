import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Union

DB_NAME = "bestiario.db"
BASE_DIR = Path(__file__).resolve().parent
SEEDS_DIR = BASE_DIR / "data" / "seeds"


def _resolve_db_path(db_path: Union[str, Path]) -> Path:
    path = Path(db_path)
    return path if path.is_absolute() else BASE_DIR / path

# =========================
# CONEXAO / UTIL
# =========================

def get_connection(db_path: Union[str, Path] = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

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

# =========================
# SCHEMA (TODAS AS TABELAS)
# =========================

SCHEMA_SQL = """
-- MUNDO / LOCALIZACOES --
CREATE TABLE IF NOT EXISTS world_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    descricao TEXT,
    biome TEXT,
    clima TEXT,
    parent_id INTEGER,
    x INTEGER,
    y INTEGER,
    FOREIGN KEY(parent_id) REFERENCES world_locations(id) ON DELETE SET NULL
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
    vigor_max INTEGER DEFAULT 10,
    vigor_atual INTEGER DEFAULT 10,
    toxicidade_max INTEGER DEFAULT 100,
    toxicidade_atual INTEGER DEFAULT 0,
    ataque INTEGER DEFAULT 2,
    defesa INTEGER DEFAULT 10,
    localizacao_id INTEGER,
    FOREIGN KEY(localizacao_id) REFERENCES world_locations(id) ON DELETE SET NULL
);
-- QUESTS ATUALIZADA --
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
    
    -- Novos Campos --
    classes_req TEXT DEFAULT 'Todas',
    criatura_id INTEGER, -- Link com tabela monsters
    alvo_monstro_nome TEXT, -- Nome texto caso não tenha link
    imagem_url TEXT -- URL da imagem gerada pelo DALL-E
);

CREATE TABLE IF NOT EXISTS quest_participantes (
    quest_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(quest_id, user_id)
);

-- NOVA TABELA: MEMÓRIA DA CAMPANHA --
CREATE TABLE IF NOT EXISTS memoria_campanha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT, -- 'Quest', 'Evento', 'Resumo'
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

-- RUMORES / GANCHOS --
CREATE TABLE IF NOT EXISTS rumores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    fonte TEXT,
    status TEXT DEFAULT 'Ativo',
    criado_em TEXT DEFAULT (datetime('now'))
);

-- NPCs COM PERSONALIDADE --
CREATE TABLE IF NOT EXISTS npc_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    personalidade TEXT NOT NULL,
    humor TEXT NOT NULL,
    habitos TEXT NOT NULL,
    voz TEXT,
    observacoes TEXT,
    criado_em TEXT DEFAULT (datetime('now'))
);

-- FACÇÕES E REPUTAÇÃO --
CREATE TABLE IF NOT EXISTS faccoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS reputacoes (
    user_id INTEGER NOT NULL,
    faccao_id INTEGER NOT NULL,
    reputacao INTEGER DEFAULT 0,
    atualizado_em TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, faccao_id),
    FOREIGN KEY (faccao_id) REFERENCES faccoes(id) ON DELETE CASCADE
);

-- CONQUISTAS --
CREATE TABLE IF NOT EXISTS conquistas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    descricao TEXT,
    categoria TEXT
);

CREATE TABLE IF NOT EXISTS usuario_conquistas (
    user_id INTEGER NOT NULL,
    conquista_id INTEGER NOT NULL,
    obtido_em TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, conquista_id),
    FOREIGN KEY (conquista_id) REFERENCES conquistas(id) ON DELETE CASCADE
);

-- LEGADO --
CREATE TABLE IF NOT EXISTS legado_beneficios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    concedido_em TEXT DEFAULT (datetime('now'))
);

-- ECONOMIA (LOJA) --
CREATE TABLE IF NOT EXISTS loja_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT,
    preco INTEGER DEFAULT 0,
    estoque INTEGER DEFAULT 1,
    efeito TEXT,
    descricao TEXT
);

-- BESTIÁRIO (SIMPLIFICADO) --
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

-- =========================
-- BESTIÁRIO (NORMALIZADO)
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

-- =========================
-- LORE (BASE AUTORAL)
-- =========================

CREATE TABLE IF NOT EXISTS lore_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  resumo TEXT,
  conteudo TEXT,
  criado_em TEXT DEFAULT (datetime('now')),
  atualizado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lore_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL, -- 'texto', 'imagem', 'arquivo', 'link'
  titulo TEXT,
  caminho_arquivo TEXT,
  url TEXT,
  mime_type TEXT,
  notas TEXT,
  criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lore_entry_sources (
  lore_entry_id INTEGER NOT NULL,
  source_id INTEGER NOT NULL,
  relevancia INTEGER DEFAULT 1,
  nota TEXT,
  PRIMARY KEY (lore_entry_id, source_id),
  FOREIGN KEY(lore_entry_id) REFERENCES lore_entries(id) ON DELETE CASCADE,
  FOREIGN KEY(source_id) REFERENCES lore_sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lore_tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS lore_entry_tags (
  lore_entry_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (lore_entry_id, tag_id),
  FOREIGN KEY(lore_entry_id) REFERENCES lore_entries(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES lore_tags(id) ON DELETE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_lore_entries_titulo ON lore_entries(titulo);
CREATE INDEX IF NOT EXISTS idx_lore_sources_tipo ON lore_sources(tipo);
"""

# =========================
# SEEDS (DADOS INICIAIS)
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

-- Loot
INSERT OR IGNORE INTO loot_items (key, label) VALUES
('monster_claw','Garra de monstro'),
('monster_tooth','Dente de monstro'),
('rotting_flesh','Carne putrefata'),
('monster_blood','Sangue de monstro'),
('mutagen_minor','Mutágeno menor'),
('essence_necrophage','Essência de necrófago');

-- Sources
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

SEED_LOCATIONS_SQL = """
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
VALUES ('Continente', 'Mundo conhecido, base para regiões e reinos.', NULL);

INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Zerrikania', 'Reino distante de guerreiras lendárias.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Deserto de Korath', 'Deserto vasto e hostil no sul.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Novigrad', 'Grande cidade portuária e centro comercial.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Velen', 'Pântanos e aldeias assoladas pela guerra.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Skellige', 'Arquipélago de clãs e tradição naval.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Kaer Morhen', 'Fortaleza dos bruxos da Escola do Lobo.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Toussaint', 'Ducado conhecido por vinho e cavalaria.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Ofir', 'Império oriental e fonte de riquezas exóticas.', id FROM world_locations WHERE nome='Continente';
INSERT OR IGNORE INTO world_locations (nome, descricao, parent_id)
SELECT 'Brokilon', 'Floresta sagrada das dríades.', id FROM world_locations WHERE nome='Continente';
"""

SEED_MONSTERS_SQL = """
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('drowner','Drowner','Necrophage',2,'tw3','core'),
('water_hag','Water Hag','Necrophage',3,'tw3','core'),
('ghoul','Ghoul','Necrophage',2,'tw3','core'),
('alghoul','Alghoul','Necrophage',4,'tw3','core'),
('rotfiend','Rotfiend','Necrophage',3,'tw3','core'),
('wraith','Wraith','Specter',3,'tw3','core'),
('nightwraith','Nightwraith','Specter',3,'tw3','core'),
('noonwraith','Noonwraith','Specter',3,'tw3','core');
"""

SEED_RELATIONS_SQL = """
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id FROM monsters m JOIN sources s ON s.key = m.origin
WHERE m.origin IS NOT NULL AND m.origin <> '';

INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão.'
FROM monsters m, weaknesses w
WHERE m.category='Specter' AND w.key IN ('specter_oil','yrden','moon_dust');

INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão.'
FROM monsters m, weaknesses w
WHERE m.category='Necrophage' AND w.key IN ('necrophage_oil','igni','aard','quen','silver');
"""

# =========================
# MIGRACOES
# =========================

def migrate_db(cursor: sqlite3.Cursor) -> None:
    """Centraliza todas as migrações"""
    
    # 1. Migração Personagens (HP Atual, MP, etc)
    personagens_extras = [
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
        ("localizacao_id", "INTEGER")
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

    # 3. Migração Quests (Restrição de Classe)
    quests_extras = [
        ("classes_req", "TEXT DEFAULT 'Todas'"),
        ("thread_id", "INTEGER"),
        ("regiao", "TEXT DEFAULT 'Desconhecida'"),
        ("max_jogadores", "INTEGER DEFAULT 1"),
        ("alvo_monstro", "TEXT"),
        ("nota_mestre", "TEXT")
    ]
    if _table_exists(cursor, "quests"):
        _add_columns_if_missing(cursor, "quests", quests_extras)

    # 4. Migração de Índices de Performance
    try:
        if _table_exists(cursor, "session_logs"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_logs_channel_id ON session_logs(channel_id);")
        if _table_exists(cursor, "quests"):
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quests_thread_id ON quests(thread_id);")
        print("⚡ Índices de performance aplicados.")
    except Exception as e:
        print(f"⚠️ Erro ao aplicar índices: {e}")

def seed_bestiary(conn: sqlite3.Connection) -> None:
    """Aplica seeds de arquivos externos e strings internas de forma segura."""
    cur = conn.cursor()
    
    # 1. Tenta carregar arquivos externos se existirem
    seed_files = [
        "seed_bestiary_ecosystem.sql",
        "seed_tw3_full_by_category.sql",
        "seed_books_core.sql",
        "seed_books_core_lote2.sql",
        "seed_tw2_full.sql",
        "seed_dlcs_hos_baw.sql",
        "seed_named_monsters_core.sql",
    ]
    
    for filename in seed_files:
        p = SEEDS_DIR / filename
        if p.exists():
            try:
                print(f"📄 Aplicando seed externo: {p.relative_to(BASE_DIR)}")
                script = p.read_text(encoding="utf-8")
                conn.executescript(script)
                conn.commit()
            except Exception as e:
                print(f"❌ Erro ao aplicar {filename}: {e}")
        else:
            pass

    # 2. Aplica seeds internos de garantia (Lookups, Monstros básicos)
    try:
        cur.executescript(SEED_LOOKUPS_SQL)
        cur.executescript(SEED_LOCATIONS_SQL)
        cur.executescript(SEED_MONSTERS_SQL)
        cur.executescript(SEED_RELATIONS_SQL)
        conn.commit()
    except Exception as e:
        print(f"⚠️ Erro nos seeds internos: {e}")

# =========================
# INIT
# =========================

def init_db(db_path: Union[str, Path] = DB_NAME) -> None:
    db_path = _resolve_db_path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(db_path) as conn:
        cur = conn.cursor()

        # 1) Schema (Cria todas as tabelas)
        cur.executescript(SCHEMA_SQL)
        
        # 2) Migrações (Atualiza tabelas antigas se necessário)
        migrate_db(cur)
        
        conn.commit()

        # 3) Seeds (Popula dados iniciais)
        seed_bestiary(conn)

if __name__ == "__main__":
    init_db(DB_NAME)
    print(f"✅ Banco inicializado e verificado: {DB_NAME}")
