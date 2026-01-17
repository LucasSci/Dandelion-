-- =========
-- CORE
-- =========
CREATE TABLE IF NOT EXISTS monsters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,            -- Necrophage, Ogroid, Vampire...
  threat_level INTEGER DEFAULT 1,     -- 1-5
  description TEXT,                  -- lore limpo
  behavior TEXT,                     -- como luta, padrões
  habitat TEXT,                      -- onde aparece
  signs TEXT,                        -- recomendados (texto simples ou normalizado depois)
  notes TEXT,                        -- observações (ex: variação rara)
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

-- =========
-- WEAKNESSES (normalizado)
-- =========
CREATE TABLE IF NOT EXISTS weaknesses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,      -- oil, bomb, sign, decoction, misc
  key TEXT NOT NULL,       -- e.g. "necrophage_oil", "yrden", "moon_dust"
  label TEXT NOT NULL      -- texto humano
);

CREATE TABLE IF NOT EXISTS monster_weaknesses (
  monster_id INTEGER NOT NULL,
  weakness_id INTEGER NOT NULL,
  priority INTEGER DEFAULT 2,  -- 1=principal, 2=útil, 3=situacional
  note TEXT,
  PRIMARY KEY (monster_id, weakness_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (weakness_id) REFERENCES weaknesses(id) ON DELETE CASCADE
);

-- =========
-- TRAITS (tags)
-- =========
CREATE TABLE IF NOT EXISTS traits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,    -- "nocturnal", "pack_hunter"
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_traits (
  monster_id INTEGER NOT NULL,
  trait_id INTEGER NOT NULL,
  PRIMARY KEY (monster_id, trait_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (trait_id) REFERENCES traits(id) ON DELETE CASCADE
);

-- =========
-- LOOT
-- =========
CREATE TABLE IF NOT EXISTS loot_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monster_loot (
  monster_id INTEGER NOT NULL,
  loot_item_id INTEGER NOT NULL,
  rarity INTEGER DEFAULT 2,     -- 1 comum, 2 incomum, 3 raro, 4 muito raro
  note TEXT,
  PRIMARY KEY (monster_id, loot_item_id),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE,
  FOREIGN KEY (loot_item_id) REFERENCES loot_items(id) ON DELETE CASCADE
);

-- =========
-- IMAGES (para geração)
-- =========
CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monster_id INTEGER NOT NULL,
  file_path TEXT,
  prompt TEXT,
  model TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE
);
