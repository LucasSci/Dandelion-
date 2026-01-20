BEGIN;

-- =====================================================
-- MONSTROS NOMEADOS / CONTRATOS ÚNICOS (CORE)
-- Critério:
--  - Criaturas únicas, ligadas a quests/contratos
--  - Canon: core
--  - Origin: tw3 (salvo exceções claras)
-- =====================================================

-- Garante sources
INSERT OR IGNORE INTO sources (key,label,canon_tier) VALUES
('tw3','The Witcher 3','core'),
('books','Livros (Sapkowski)','core');

-- =========================
-- SPECTERS (TW3)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('devil_by_the_well','Devil by the Well','Specter',4,'tw3','core','Contrato em White Orchard. Noonwraith ligada a ossos e poço.'),
('jenny_o_the_woods','Jenny o'' the Woods','Specter',4,'tw3','core','Nightwraith agressiva; resposta incorreta a oferendas piora o combate.'),
('penitent_named','The Penitent','Specter',4,'tw3','core','Espírito ligado à culpa e punição ritual.'),
('red_miasmal_named','Red Miasmal','Specter',4,'tw3','core','Entidade espectral associada a masmorras e contaminação.'),
('the_white_lady','The White Lady','Specter',4,'tw3','core','Aparição ligada a tragédia local e luto recorrente.');

-- =========================
-- NECROPHAGES (TW3)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('mourntart','Mourntart','Necrophage',5,'tw3','core','Fiend canibal que se alimentou de outros fiends. Extremamente perigoso.'),
('spoon_wight','Spotted Wight','Necrophage',4,'tw3','core','Maldição de hospitalidade quebrada; removível por ritual narrativo.'),
('grave_hag_named','Grave Hag (Unique)','Necrophage',4,'tw3','core','Variante única ligada a cemitério específico.');

-- =========================
-- RELICTS / CURSED (TW3)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('botchling_named','Botchling','Relict',4,'tw3','core','Criatura amaldiçoada; pode ser apaziguada (lubberkin).'),
('lubberkin','Lubberkin','Relict',3,'tw3','core','Forma apaziguada do botchling; não hostil.'),
('hym_named','Hym','Specter',5,'tw3','core','Parasita do medo; só derrotável via escolha narrativa.'),
('caretaker_named','Caretaker','Relict',5,'tw3','core','Guardião do espelho; invoca entidades com pá ritual.');

-- =========================
-- VAMPIRES (TW3)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('sarasti','Sarasti','Vampire',4,'tw3','core','Katakana antigo, extremamente ágil.'),
('hubert_rejk','Hubert Rejk','Vampire',5,'tw3','core','Higher Vampire disfarçado; investigação urbana.'),
('detlaff','Dettlaff van der Eretein','Vampire',5,'tw3','core','Higher Vampire. Boss narrativo (Blood and Wine).');

-- =========================
-- DRACONIDS / HYBRIDS (TW3)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('royal_griffin_white_orchard','Royal Griffin','Hybrid',5,'tw3','core','Contrato inicial icônico. Controle aéreo essencial.');

-- =========================
-- LIVROS – NOMEADOS (quando aplicável)
-- =========================
INSERT OR IGNORE INTO monsters
(slug,name,category,threat_level,origin,canon_tier,notes)
VALUES
('nivellen','Nivellen','Cursed One',3,'books','core','Homem amaldiçoado; resolução não violenta possível.'),
('verena','Vereena','Vampire',4,'books','core','Bruxa (bruxa/bruxae) ligada ao conto “A Grain of Truth”.');

-- =========================
-- VARIANTS / ALIASES
-- =========================

-- Devil by the Well
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT id, 'Noonwraith of White Orchard', 'Nome descritivo usado em guias.'
FROM monsters WHERE slug='devil_by_the_well';

-- Botchling
INSERT OR IGNORE INTO variants (monster_id, name, description)
SELECT id, 'Lubberkin (Potential)', 'Forma alternativa após ritual.'
FROM monsters WHERE slug='botchling_named';

-- =========================
-- MONSTER_SOURCES (auto)
-- =========================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = m.origin
WHERE m.origin IS NOT NULL;

-- =========================
-- FRAQUEZAS (AJUSTES FINOS)
-- =========================

-- Specters nomeados
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Controle espectral.'
FROM monsters m, weaknesses w
WHERE m.slug IN (
  'devil_by_the_well','jenny_o_the_woods','penitent_named',
  'red_miasmal_named','the_white_lady'
)
AND w.key IN ('specter_oil','yrden','moon_dust');

-- Vampiros nomeados
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Ferramentas contra vampiros superiores.'
FROM monsters m, weaknesses w
WHERE m.slug IN ('sarasti','hubert_rejk','detlaff')
AND w.key IN ('vampire_oil','moon_dust','quen','silver');

-- =========================
-- LOOT (CONTROLADO)
-- =========================
INSERT OR IGNORE INTO monster_loot (monster_id, loot_item_id, rarity, note)
SELECT m.id, l.id, 3, 'Loot especial de contrato.'
FROM monsters m, loot_items l
WHERE m.slug IN (
  'mourntart','sarasti','hubert_rejk','detlaff','royal_griffin_white_orchard'
)
AND l.key IN ('mutagen_regular','essence_relict','essence_specter');

COMMIT;
