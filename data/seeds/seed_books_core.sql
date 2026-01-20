BEGIN;

-- =========================================
-- LIVROS (SAPKOWSKI) - CORE
-- origin = 'books' | canon_tier = 'core'
-- =========================================

-- IMPORTANT: garante que existe o source 'books'
INSERT OR IGNORE INTO sources (key,label,canon_tier)
VALUES ('books','Livros (Sapkowski)','core');

-- =========================
-- CURSED ONES (books)
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('striga_books','Striga','Cursed One',5,'books','core');

-- =========================
-- VAMPIRES (books)
-- Bruxa (bruxa/bruxae) aparece nos contos (ex.: A Grain of Truth) :contentReference[oaicite:1]{index=1}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('bruxa_books','Bruxa','Vampire',4,'books','core');

-- =========================
-- INSECTOIDS (books)
-- Kikimora é citada no cânone dos livros :contentReference[oaicite:2]{index=2}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('kikimora_books','Kikimora','Insectoid',4,'books','core');

-- =========================
-- RELICTS (books)
-- Leshy + Vodyanoy são citados no cânone dos livros :contentReference[oaicite:3]{index=3}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('leshy_books','Leshy','Relict',5,'books','core'),
('vodyanoy_books','Vodyanoy','Relict',3,'books','core');

-- =========================
-- HYBRIDS (books)
-- Manticore/Chimera são citadas no cânone dos livros :contentReference[oaicite:4]{index=4}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('manticore_books','Manticore','Hybrid',5,'books','core'),
('chimera_books','Chimera','Hybrid',5,'books','core');

-- =========================
-- DRACONIDS (books)
-- Dragon/Wyvern citados no cânone dos livros :contentReference[oaicite:5]{index=5}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('dragon_books','Dragon','Draconid',5,'books','core'),
('wyvern_books','Wyvern','Draconid',4,'books','core');

-- =========================
-- NECROPHAGES (books)
-- Ghoul citado no cânone dos livros :contentReference[oaicite:6]{index=6}
-- =========================
INSERT OR IGNORE INTO monsters (slug,name,category,threat_level,origin,canon_tier)
VALUES
('ghoul_books','Ghoul','Necrophage',3,'books','core');

-- =========================================
-- MONSTER_SOURCES (link automático)
-- =========================================
INSERT OR IGNORE INTO monster_sources (monster_id, source_id)
SELECT m.id, s.id
FROM monsters m
JOIN sources s ON s.key = 'books'
WHERE m.origin = 'books';

COMMIT;
