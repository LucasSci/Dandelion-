BEGIN;

-- =====================================================
-- LIVROS (SAPKOWSKI) – LOTE 2
-- origin = 'books' | canon_tier = 'core'
-- =====================================================

-- Garante source
INSERT OR IGNORE INTO sources (key,label,canon_tier)
VALUES ('books','Livros (Sapkowski)','core');

-- =========================
-- RELICTS / FOLK CREATURES
-- =========================

INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('aguara_books','Aguara','Relict',4,'books','core'),
('lamia_books','Lamia','Hybrid',4,'books','core'),
('doppler_books','Doppler','Relict',3,'books','core'),
('silvan_books','Silvan','Relict',2,'books','core'),
('kobold_books','Kobold','Ogroid',2,'books','core');

-- =========================
-- SPECTERS / CURSED
-- =========================

INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('nightmare_books','Nightmare','Specter',3,'books','core'),
('revenant_books','Revenant','Specter',4,'books','core'),
('banshee_books','Banshee','Specter',4,'books','core');

-- =========================
-- BEASTS / MONSTROUS ANIMALS
-- (não-humanos, não mágicos puros)
-- =========================

INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('giant_centipede_books','Giant Centipede','Insectoid',3,'books','core'),
('giant_spider_books','Giant Spider','Insectoid',3,'books','core'),
('giant_scorpion_books','Giant Scorpion','Insectoid',4,'books','core');

-- =========================
-- VARIANTS / ALIASES (tradução)
-- =========================

-- Aguara (variações de grafia)
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT m.id, 'Aguaara', 'Variação de transliteração encontrada em algumas traduções.'
FROM monsters m WHERE m.slug='aguara_books';

-- Doppler
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT m.id, 'Changeling', 'Nome comum usado em traduções e adaptações.'
FROM monsters m WHERE m.slug='doppler_books';

-- Silvan
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT m.id, 'Fauno', 'Nome folclórico associado em algumas edições.'
FROM monsters m WHERE m.slug='silvan_books';

-- =========================
-- MONSTER_SOURCES (link)
-- =========================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key='books'
WHERE m.origin='books';

-- =========================
-- FRAQUEZAS BASE (livros)
-- Mantidas genéricas; você especializa depois
-- =========================

-- Specters
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Ferramentas clássicas contra espectros.'
FROM monsters m, weaknesses w
WHERE m.origin='books'
AND m.category='Specter'
AND w.key IN ('specter_oil','yrden','moon_dust');

-- Relicts / Folk
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Criaturas antigas e inteligentes.'
FROM monsters m, weaknesses w
WHERE m.origin='books'
AND m.category IN ('Relict','Hybrid')
AND w.key IN ('relict_oil','igni','quen','silver');

-- Ogroids
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Criaturas humanoides não-mágicas.'
FROM monsters m, weaknesses w
WHERE m.origin='books'
AND m.category='Ogroid'
AND w.key IN ('ogroid_oil','aard','quen','silver');

-- =========================
-- LOOT GENÉRICO
-- =========================

INSERT OR IGNORE INTO monster_loot (monster_id, loot_item_id, rarity, note)
SELECT m.id, l.id, 2, 'Material genérico descrito nos livros.'
FROM monsters m, loot_items l
WHERE m.origin='books'
AND l.key IN ('monster_claw','monster_tooth','monster_blood');

COMMIT;
