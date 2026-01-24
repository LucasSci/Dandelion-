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
    titulo TEXT,
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

CREATE TABLE IF NOT EXISTS personagem_memorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personagem_id INTEGER NOT NULL,
    sessao_id INTEGER NOT NULL,
    criado_em TEXT DEFAULT (datetime('now')),
    UNIQUE(personagem_id, sessao_id),
    FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE,
    FOREIGN KEY(sessao_id) REFERENCES memoria_campanha(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_personagem_memorias_personagem_id ON personagem_memorias(personagem_id);
CREATE INDEX IF NOT EXISTS idx_personagem_memorias_sessao_id ON personagem_memorias(sessao_id);

-- CAMPANHA SOLO --
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

CREATE TABLE IF NOT EXISTS solo_story_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    capitulo INTEGER DEFAULT 1,
    entrada TEXT NOT NULL,
    criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS solo_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    quantidade INTEGER DEFAULT 0,
    atualizado_em TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, nome)
);
CREATE TABLE IF NOT EXISTS habilidades_personagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personagem_id INTEGER,
    nome TEXT,
    descricao TEXT,
    dado TEXT,
    FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS atributos_personagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personagem_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    valor INTEGER DEFAULT 0,
    UNIQUE(personagem_id, nome),
    FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS armaduras_personagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personagem_id INTEGER NOT NULL,
    localizacao TEXT NOT NULL,
    sp INTEGER DEFAULT 0,
    reliability INTEGER DEFAULT 100,
    UNIQUE(personagem_id, localizacao),
    FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS armadura_modificadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    armadura_id INTEGER NOT NULL,
    tipo_dano TEXT NOT NULL,
    multiplicador REAL DEFAULT 1.0,
    UNIQUE(armadura_id, tipo_dano),
    FOREIGN KEY(armadura_id) REFERENCES armaduras_personagem(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    nome TEXT,
    tipo TEXT,
    valor INTEGER,
    efeito TEXT
);

-- ALQUIMIA & CRAFTING --
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

CREATE TABLE IF NOT EXISTS alchemy_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    base_alcoolica TEXT NOT NULL,
    efeito TEXT NOT NULL,
    toxicidade_base INTEGER DEFAULT 10,
    qualidade_min INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS alchemy_recipe_ingredients (
    recipe_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantidade INTEGER DEFAULT 1,
    PRIMARY KEY (recipe_id, ingredient_id),
    FOREIGN KEY(recipe_id) REFERENCES alchemy_recipes(id) ON DELETE CASCADE,
    FOREIGN KEY(ingredient_id) REFERENCES alchemy_ingredients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alchemy_user_ingredients (
    user_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    quantidade INTEGER DEFAULT 0,
    qualidade INTEGER DEFAULT 0,
    atualizado_em TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, ingredient_id),
    FOREIGN KEY(ingredient_id) REFERENCES alchemy_ingredients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alchemy_user_recipes (
    user_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    unlocked_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, recipe_id),
    FOREIGN KEY(recipe_id) REFERENCES alchemy_recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    user_name TEXT,
    content TEXT,
    is_bot BOOLEAN,
    timestamp TEXT DEFAULT (datetime('now'))
);

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

CREATE TABLE IF NOT EXISTS transcription_settings (
    guild_id INTEGER PRIMARY KEY,
    transcription_channel_id INTEGER,
    summary_channel_id INTEGER
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

CREATE TABLE IF NOT EXISTS economia_regional (
    localizacao_id INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    modificador REAL DEFAULT 1.0,
    atualizado_em TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (localizacao_id, categoria),
    FOREIGN KEY(localizacao_id) REFERENCES world_locations(id) ON DELETE CASCADE
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
    dano_base TEXT DEFAULT '1d6',
    lore_cd INTEGER
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
  is_private BOOLEAN DEFAULT 0,
  owner_id INTEGER,
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
