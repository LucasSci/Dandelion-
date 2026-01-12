import sqlite3

DB_NAME = "bestiario.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # --- PERSONAGENS (Mantido) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nome TEXT UNIQUE,
                raca TEXT,
                classe TEXT,
                nivel INTEGER DEFAULT 1,
                historia TEXT,
                imagem_url TEXT,
                ouro INTEGER DEFAULT 0
            )
        """)

        # --- CRIATURAS (ATUALIZADO COM STATUS) ---
        # Adicionamos HP Máximo, Iniciativa e Dano Base
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS criaturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                descricao TEXT,
                fraquezas TEXT,
                imagem_url TEXT,
                hp_max INTEGER DEFAULT 50,
                iniciativa INTEGER DEFAULT 10,
                dano_base TEXT DEFAULT '1d6'
            )
        """)
        
        # --- HABILIDADES DAS CRIATURAS (NOVO) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habilidades_criatura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criatura_id INTEGER,
                nome TEXT,
                descricao TEXT,
                dano_formula TEXT,
                FOREIGN KEY(criatura_id) REFERENCES criaturas(id) ON DELETE CASCADE
            )
        """)

        # --- HABILIDADES DOS JOGADORES (Mantido) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habilidades_personagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personagem_id INTEGER,
                nome TEXT,
                descricao TEXT,
                dado TEXT,
                FOREIGN KEY(personagem_id) REFERENCES personagens(id) ON DELETE CASCADE
            )
        """)
        
        # (Outras tabelas mantidas...)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                nome TEXT,
                tipo TEXT,
                valor INTEGER,
                efeito TEXT
            )
        """)
        
        conn.commit()