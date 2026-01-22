from __future__ import annotations

from pathlib import Path

from .connection import BASE_DIR

SEEDS_DIR = BASE_DIR / "data" / "seeds"

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

SEED_ALCHEMY_SQL = """
INSERT OR IGNORE INTO alchemy_ingredients (nome, tipo, biome, raridade, qualidade_min, qualidade_max, descricao) VALUES
('Álcool base', 'Base', 'Qualquer', 1, 60, 100, 'Destilado neutro usado como base de poções.'),
('Arenária', 'Erva', 'Planície', 1, 40, 100, 'Erva comum de planícies ventosas.'),
('Verbena', 'Erva', 'Floresta', 2, 45, 100, 'Folhas usadas para estabilizar misturas.'),
('Ranúnculo do pântano', 'Erva', 'Pântano', 3, 35, 90, 'Flores viscosas com aroma acre.'),
('Cogumelo da gruta', 'Erva', 'Caverna', 2, 40, 95, 'Fungo fosforescente, ótimo para cataplasmas.'),
('Sangue de monstro', 'Ingrediente de Monstro', 'Qualquer', 3, 30, 85, 'Essência vital de criaturas perigosas.'),
('Garra de monstro', 'Ingrediente de Monstro', 'Qualquer', 4, 25, 80, 'Fragmentos usados em decoctos.'),
('Raiz amarga', 'Erva', 'Floresta', 2, 40, 95, 'Raiz que dá potência a poções de resistência.');

INSERT OR IGNORE INTO alchemy_recipes (nome, base_alcoolica, efeito, toxicidade_base, qualidade_min) VALUES
('Andorinha', 'Álcool base', 'Recupera vitalidade ao longo de alguns turnos.', 15, 55),
('Gato', 'Álcool base', 'Aumenta visão em baixa luz por algumas horas.', 12, 50),
('Relâmpago', 'Álcool base', 'Eleva vigor e reflexos por pouco tempo.', 20, 60);

INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 2
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Andorinha' AND i.nome = 'Verbena';
INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 1
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Andorinha' AND i.nome = 'Raiz amarga';

INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 2
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Gato' AND i.nome = 'Arenária';
INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 1
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Gato' AND i.nome = 'Cogumelo da gruta';

INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 2
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Relâmpago' AND i.nome = 'Ranúnculo do pântano';
INSERT OR IGNORE INTO alchemy_recipe_ingredients (recipe_id, ingredient_id, quantidade)
SELECT r.id, i.id, 1
FROM alchemy_recipes r JOIN alchemy_ingredients i ON r.nome = 'Relâmpago' AND i.nome = 'Sangue de monstro';
"""


def seed_bestiary(conn) -> None:
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
        cur.executescript(SEED_ALCHEMY_SQL)
        conn.commit()
    except Exception as e:
        print(f"⚠️ Erro nos seeds internos: {e}")
