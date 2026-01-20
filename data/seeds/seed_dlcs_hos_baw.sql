BEGIN;

-- =====================================================
-- THE WITCHER 3 DLCs
-- Hearts of Stone (hos) + Blood and Wine (baw)
-- canon_tier = core
-- =====================================================

-- Garante sources
INSERT OR IGNORE INTO sources (key,label,canon_tier) VALUES
('hos','Hearts of Stone','core'),
('baw','Blood and Wine','core');

-- =========================
-- HEARTS OF STONE (HoS)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('gaunter_o_dimm','Gaunter O''Dimm','Human',5,'hos','core','Entidade/antagonista. Não é “monstro” de combate padrão, mas é bestiário narrativo.'),
('olgierd_von_everec','Olgierd von Everec','Human',4,'hos','core','Humano amaldiçoado e central na narrativa.'),
('caretaker_hos','Caretaker','Relict',5,'hos','core','Guardião macabro; combate único.'),
('iris_greatest_fear','Iris'' Greatest Fear','Specter',5,'hos','core','Entidade ligada a trauma/medo.'),
('ethereal_hos','Ethereal','Specter',4,'hos','core','Entidades espectrais que drenam e punem aproximação.'),
('ofieri_mage_hos','Ofieri Mage','Human',4,'hos','core','Inimigo humano exclusivo do arco Ofieri.');

-- =========================
-- BLOOD AND WINE (BaW)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('detlaff_baw','Dettlaff van der Eretein','Vampire',5,'baw','core','Higher Vampire; boss narrativo.'),
('bruxa_baw','Bruxa','Vampire',4,'baw','core','Bruxa/bruxae em Toussaint (aparece com força em BaW).'),
('alp_baw','Alp','Vampire',4,'baw','core','Predador noturno; variante vampírica.'),
('higher_vampire_baw','Higher Vampire','Vampire',5,'baw','core','Categoria narrativa: “vampiro superior”.'),
('shaelmaar','Shaelmaar','Beast',5,'baw','core','Criatura blindada subterrânea; combate de arena.'),
('slyzard','Slyzard','Draconid',5,'baw','core','Predador alado; draconídeo de Toussaint.'),
('giant_toad','Giant Toad','Beast',5,'baw','core','Criatura gigante associada a contrato/quest.'),
('hanse_thugs','Hanse Bandits','Human',4,'baw','core','Inimigos humanos (Hanse).');

-- =========================
-- VARIANTS / ALIASES (DLCs)
-- =========================

-- Dettlaff: variante já existe como detlaff em outro seed; mantém ambos sem conflito
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT m.id, 'Dettlaff (BaW Boss)', 'Entrada específica da campanha Blood and Wine.'
FROM monsters m WHERE m.slug='detlaff_baw';

-- Ethereal
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT m.id, 'Ethereals', 'Nome plural comum em guias e referências.'
FROM monsters m WHERE m.slug='ethereal_hos';

-- =========================
-- MONSTER_SOURCES (auto)
-- =========================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = m.origin
WHERE m.origin IN ('hos','baw');

-- =========================
-- FRAQUEZAS (DLC)
-- Mantidas genéricas e coerentes com categorias
-- =========================

-- Specters DLC
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Padrão para espectros.'
FROM monsters m, weaknesses w
WHERE m.origin='hos'
AND m.category='Specter'
AND w.key IN ('specter_oil','yrden','moon_dust');

-- Vampires BaW
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Ferramentas contra vampiros.'
FROM monsters m, weaknesses w
WHERE m.origin='baw'
AND m.category='Vampire'
AND w.key IN ('vampire_oil','moon_dust','quen','silver');

-- Draconid BaW
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Controle aéreo e fogo.'
FROM monsters m, weaknesses w
WHERE m.origin='baw'
AND m.category='Draconid'
AND w.key IN ('draconid_oil','aard','igni','silver');

-- Beasts BaW (genérico)
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Ferramentas gerais.'
FROM monsters m, weaknesses w
WHERE m.origin='baw'
AND m.category='Beast'
AND w.key IN ('quen','igni','aard','steel');

-- =========================
-- LOOT (DLC)
-- =========================
INSERT OR IGNORE INTO monster_loot (monster_id, loot_item_id, rarity, note)
SELECT m.id, l.id, 3, 'Loot especial de DLC.'
FROM monsters m, loot_items l
WHERE m.origin IN ('hos','baw')
AND m.category NOT IN ('Human')
AND l.key IN ('mutagen_regular','essence_relict','essence_specter');

COMMIT;
