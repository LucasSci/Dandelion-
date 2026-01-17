BEGIN;

-- =====================================================
-- THE WITCHER 3 – BESTIÁRIO BASE (POR CATEGORIA)
-- Canon: core | Origin: tw3
-- =====================================================

-- =========================
-- NECROPHAGE
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('drowner','Drowner','Necrophage',2,'tw3','core'),
('drowned_dead','Drowned Dead','Necrophage',3,'tw3','core'),
('ghoul','Ghoul','Necrophage',2,'tw3','core'),
('alghoul','Alghoul','Necrophage',4,'tw3','core'),
('rotfiend','Rotfiend','Necrophage',3,'tw3','core'),
('grave_hag','Grave Hag','Necrophage',4,'tw3','core'),
('water_hag','Water Hag','Necrophage',3,'tw3','core'),
('foglet','Foglet','Necrophage',3,'tw3','core'),
('scurver','Scurver','Necrophage',3,'tw3','core'),
('spotted_wight','Spotted Wight','Necrophage',4,'tw3','core'),
('wight','Wight','Necrophage',4,'tw3','core');

-- =========================
-- SPECTER
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('wraith','Wraith','Specter',3,'tw3','core'),
('nightwraith','Nightwraith','Specter',3,'tw3','core'),
('noonwraith','Noonwraith','Specter',3,'tw3','core'),
('plague_maiden','Plague Maiden','Specter',4,'tw3','core'),
('hym','Hym','Specter',5,'tw3','core'),
('penitent','Penitent','Specter',4,'tw3','core'),
('red_miasmal','Red Miasmal','Specter',4,'tw3','core');

-- =========================
-- OGROID
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('nekker','Nekker','Ogroid',2,'tw3','core'),
('nekker_warrior','Nekker Warrior','Ogroid',3,'tw3','core'),
('cyclops','Cyclops','Ogroid',5,'tw3','core'),
('rock_troll','Rock Troll','Ogroid',3,'tw3','core'),
('ice_troll','Ice Troll','Ogroid',4,'tw3','core');

-- =========================
-- RELICT
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('fiend','Fiend','Relict',5,'tw3','core'),
('chort','Chort','Relict',5,'tw3','core'),
('leshen_tw3','Leshen','Relict',5,'tw3','core'),
('botchling','Botchling','Relict',4,'tw3','core');

-- =========================
-- VAMPIRE
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('ekimmara','Ekimmara','Vampire',4,'tw3','core'),
('katakan','Katakan','Vampire',4,'tw3','core'),
('alp','Alp','Vampire',4,'tw3','core'),
('higher_vampire','Higher Vampire','Vampire',5,'tw3','core');

-- =========================
-- DRACONID
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('wyvern','Wyvern','Draconid',4,'tw3','core'),
('royal_wyvern','Royal Wyvern','Draconid',5,'tw3','core'),
('basilisk','Basilisk','Draconid',5,'tw3','core');

-- =========================
-- INSECTOID
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('endrega_worker','Endrega Worker','Insectoid',3,'tw3','core'),
('endrega_warrior','Endrega Warrior','Insectoid',4,'tw3','core'),
('arachas','Arachas','Insectoid',4,'tw3','core'),
('arachas_drone','Arachas Drone','Insectoid',3,'tw3','core');

-- =========================
-- CURSED ONE
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('werewolf','Werewolf','Cursed One',4,'tw3','core'),
('wolf_werewolf','Wolf Werewolf','Cursed One',4,'tw3','core'),
('bear_werewolf','Bear Werewolf','Cursed One',5,'tw3','core');

-- =========================
-- HYBRID
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier) VALUES
('harpy','Harpy','Hybrid',3,'tw3','core'),
('sirene','Sirene','Hybrid',3,'tw3','core'),
('griffin','Griffin','Hybrid',5,'tw3','core'),
('royal_griffin','Royal Griffin','Hybrid',5,'tw3','core');

-- =====================================================
-- MONSTER_SOURCES (auto)
-- =====================================================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = 'tw3'
WHERE m.origin = 'tw3';

-- =====================================================
-- FRAQUEZAS PADRÃO POR CATEGORIA
-- =====================================================

-- Necrophage
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Padrão para necrófagos.'
FROM monsters m, weaknesses w
WHERE m.category='Necrophage'
AND w.key IN ('necrophage_oil','silver','igni','aard','quen');

-- Specter
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Padrão para espectros.'
FROM monsters m, weaknesses w
WHERE m.category='Specter'
AND w.key IN ('specter_oil','yrden','moon_dust');

-- Ogroid
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Controle e resistência.'
FROM monsters m, weaknesses w
WHERE m.category='Ogroid'
AND w.key IN ('ogroid_oil','quen','aard','silver');

-- Relict
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Respostas para relíquias.'
FROM monsters m, weaknesses w
WHERE m.category='Relict'
AND w.key IN ('relict_oil','igni','quen','silver');

-- Vampire
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Ferramentas contra vampiros.'
FROM monsters m, weaknesses w
WHERE m.category='Vampire'
AND w.key IN ('vampire_oil','moon_dust','quen','silver');

-- Draconid
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Controle aéreo e fogo.'
FROM monsters m, weaknesses w
WHERE m.category='Draconid'
AND w.key IN ('draconid_oil','aard','igni','silver');

-- =====================================================
-- LOOT GENÉRICO
-- =====================================================
INSERT OR IGNORE INTO monster_loot (monster_id, loot_item_id, rarity, note)
SELECT m.id, l.id, 2, ''
FROM monsters m, loot_items l
WHERE m.origin='tw3'
AND l.key IN ('monster_claw','monster_tooth','monster_blood');

COMMIT;
