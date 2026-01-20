-- seed_bestiary_ecosystem.sql
-- Objetivo: seed “limpo” (lookups + sources + um lote inicial CANÔNICO por fonte)
-- Observação: este arquivo é um STARTER PACK (não é 100% exaustivo do universo).
-- Você vai ampliando em lotes, mantendo consistência de slug/origin/canon_tier.

BEGIN;

-- =========================
-- SOURCES (ECOSSISTEMA)
-- =========================
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

-- =========================
-- WEAKNESSES (BASE)
-- =========================
INSERT OR IGNORE INTO weaknesses (type, key, label) VALUES
-- oils
('oil','necrophage_oil','Óleo contra Necrófagos'),
('oil','specter_oil','Óleo contra Espectros'),
('oil','hanged_mans_venom','Veneno do Enforcado'),
('oil','cursed_oil','Óleo contra Amaldiçoados'),
('oil','insectoid_oil','Óleo contra Insetoides'),
('oil','ogroid_oil','Óleo contra Ogroides'),
('oil','relict_oil','Óleo contra Relíquias'),
('oil','vampire_oil','Óleo contra Vampiros'),
('oil','draconid_oil','Óleo contra Draconídeos'),

-- bombs
('bomb','samum','Samum'),
('bomb','grapeshot','Bomba de Pólvora'),
('bomb','dancing_star','Estrela Dançante'),
('bomb','devils_puffball','Sopro do Diabo'),
('bomb','moon_dust','Pó da Lua'),
('bomb','northern_wind','Vento do Norte'),

-- signs
('sign','igni','Igni'),
('sign','yrden','Yrden'),
('sign','aard','Aard'),
('sign','quen','Quen'),
('sign','axii','Axii'),

-- misc
('misc','fire','Fogo'),
('misc','silver','Prata'),
('misc','steel','Aço'),
('misc','keep_distance','Manter distância / controlar alcance');

-- =========================
-- TRAITS (BASE)
-- =========================
INSERT OR IGNORE INTO traits (key, label) VALUES
('pack_hunter','Caça em bando'),
('nocturnal','Noturno'),
('carrion_feeder','Alimenta-se de carniça'),
('ambusher','Emboscador'),
('regenerative','Regenerativo'),
('poisonous','Venenoso'),
('waterbound','Vinculado à água'),
('disease_risk','Risco de praga/doença'),
('territorial','Territorial'),
('ethereal','Corpo etéreo / intangível'),
('cursed','Amaldiçoado'),
('armored','Blindagem natural'),
('flying','Voador');

-- =========================
-- LOOT (BASE)
-- =========================
INSERT OR IGNORE INTO loot_items (key, label) VALUES
('monster_claw','Garra de monstro'),
('monster_tooth','Dente de monstro'),
('monster_hide','Couro/Pele de monstro'),
('rotting_flesh','Carne putrefata'),
('monster_blood','Sangue de monstro'),
('mutagen_minor','Mutágeno menor'),
('mutagen_regular','Mutágeno'),
('essence_necrophage','Essência de necrófago'),
('essence_specter','Essência de espectro'),
('essence_relict','Essência de relíquia');

-- ==========================================================
-- MONSTERS (STARTER PACK) - slugs estáveis + origin + tier
-- Preencha description/behavior/habitat/signs/notes depois.
-- ==========================================================

-- =========================
-- LIVROS (BOOKS) - exemplos clássicos
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('striga','Striga','Cursed One',5,'books','core'),
('bruxa','Bruxa','Cursed One',4,'books','core'),
('kikimora','Kikimora','Insectoid',4,'books','core'),
('leshen','Leshen','Relict',5,'books','core'),
('vodyanoy','Vodyanoy','Relict',3,'books','core'),
('manticore','Manticore','Hybrid',5,'books','core');

-- =========================
-- TW1 - exemplos
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('barghest_tw1','Barghest','Specter',3,'tw1','core'),
('hellhound_tw1','Hellhound','Specter',4,'tw1','core'),
('fleder_tw1','Fleder','Vampire',4,'tw1','core'),
('kikimore_worker_tw1','Kikimore Worker','Insectoid',3,'tw1','core');

-- =========================
-- TW2 - exemplos
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('harpy_tw2','Harpy','Hybrid',3,'tw2','core'),
('gargoyle_tw2','Gargoyle','Elementa',4,'tw2','core'),
('endrega_worker_tw2','Endrega Worker','Insectoid',3,'tw2','core'),
('kayran','Kayran','Insectoid',5,'tw2','core');

-- =========================
-- TW3 - base grande (um lote inicial realista)
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
-- Necrophage
('drowner','Drowner','Necrophage',2,'tw3','core'),
('drowned_dead','Drowned Dead','Necrophage',3,'tw3','core'),
('ghoul','Ghoul','Necrophage',2,'tw3','core'),
('alghoul','Alghoul','Necrophage',4,'tw3','core'),
('rotfiend','Rotfiend','Necrophage',3,'tw3','core'),
('grave_hag','Grave Hag','Necrophage',4,'tw3','core'),
('water_hag','Water Hag','Necrophage',3,'tw3','core'),

-- Specter
('wraith','Wraith','Specter',3,'tw3','core'),
('nightwraith','Nightwraith','Specter',3,'tw3','core'),
('noonwraith','Noonwraith','Specter',3,'tw3','core'),
('plague_maiden','Plague Maiden','Specter',4,'tw3','core'),

-- Ogroid
('nekker','Nekker','Ogroid',2,'tw3','core'),
('nekker_warrior','Nekker Warrior','Ogroid',3,'tw3','core'),
('rock_troll','Rock Troll','Ogroid',3,'tw3','core'),
('ice_troll','Ice Troll','Ogroid',4,'tw3','core'),
('cyclops','Cyclops','Ogroid',5,'tw3','core'),

-- Vampire
('ekimmara','Ekimmara','Vampire',4,'tw3','core'),
('katakan','Katakan','Vampire',4,'tw3','core'),

-- Relict
('fiend','Fiend','Relict',5,'tw3','core'),
('chort','Chort','Relict',5,'tw3','core'),
('leshen_tw3','Leshen','Relict',5,'tw3','core'),

-- Draconid
('wyvern','Wyvern','Draconid',4,'tw3','core'),
('basilisk','Basilisk','Draconid',5,'tw3','core'),

-- Insectoid
('endrega_worker','Endrega Worker','Insectoid',3,'tw3','core'),
('endrega_warrior','Endrega Warrior','Insectoid',4,'tw3','core'),

-- Cursed One
('werewolf','Werewolf','Cursed One',4,'tw3','core');

-- =========================
-- HOS / BAW - exemplos (DLCs)
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('caretaker_hos','Caretaker','Relict',5,'hos','core'),
('ofieri_mage_hos','Ofieri Mage','Human',4,'hos','core'),
('alp_baw','Alp','Vampire',4,'baw','core'),
('bruxa_baw','Bruxa','Cursed One',4,'baw','core');

-- =========================
-- Gwent / Thronebreaker / Comics - exemplos (extended)
-- =========================
INSERT OR IGNORE INTO monsters (slug, name, category, threat_level, origin, canon_tier)
VALUES
('arachas_gwent','Arachas','Insectoid',4,'gwent','extended'),
('detlaff_gwent','Dettlaff','Vampire',5,'gwent','extended'),
('striga_thronebreaker','Striga','Cursed One',5,'thronebreaker','extended'),
('leshen_comics','Leshen','Relict',5,'comics','extended');

-- =========================================
-- MONSTER_SOURCES: link automático por origin
-- =========================================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = m.origin
WHERE m.origin IS NOT NULL AND m.origin <> '';

-- =========================================
-- RELAÇÕES: defaults por categoria (simples)
-- Ajuste depois por criatura individual
-- =========================================

-- Specters: espectro oil + yrden + moon dust
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão para espectros.'
FROM monsters m, weaknesses w
WHERE m.category='Specter' AND w.key IN ('specter_oil','yrden','moon_dust');

-- Necrophages: necro oil + silver + sinais úteis
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 1, 'Resposta padrão para necrófagos.'
FROM monsters m, weaknesses w
WHERE m.category='Necrophage' AND w.key IN ('necrophage_oil','silver','igni','aard','quen');

-- Ogroids: ogroid oil + quen + aard (exemplo)
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Respostas comuns para ogroides.'
FROM monsters m, weaknesses w
WHERE m.category='Ogroid' AND w.key IN ('ogroid_oil','quen','aard','silver');

-- Vampires: vampire oil + moon dust (muitos vampiros odeiam truques)
INSERT OR IGNORE INTO monster_weaknesses (monster_id, weakness_id, priority, note)
SELECT m.id, w.id, 2, 'Respostas comuns para vampiros.'
FROM monsters m, weaknesses w
WHERE m.category='Vampire' AND w.key IN ('vampire_oil','moon_dust','quen','silver');

-- Loot genérico para tudo que não é humano
INSERT OR IGNORE INTO monster_loot (monster_id, loot_item_id, rarity, note)
SELECT m.id, l.id, 2, ''
FROM monsters m, loot_items l
WHERE m.category NOT IN ('Human') AND l.key IN ('monster_claw','monster_tooth','monster_blood');

COMMIT;
