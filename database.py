import sqlite3

DB_NAME = "bestiario.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # --- PERSONAGENS (ATUALIZADO) ---
        # Adicionei colunas: hp_max, mp_max, ataque, defesa
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
                ouro INTEGER DEFAULT 0,
                hp_max INTEGER DEFAULT 30,
                mp_max INTEGER DEFAULT 10,
                ataque INTEGER DEFAULT 2,
                defesa INTEGER DEFAULT 10
            )
        """)
        
        # Tenta adicionar colunas caso a tabela já exista (Migração simples)
        colunas_extras = [
            ("hp_max", "INTEGER DEFAULT 30"),
            ("mp_max", "INTEGER DEFAULT 10"),
            ("ataque", "INTEGER DEFAULT 2"),
            ("defesa", "INTEGER DEFAULT 10")
        ]
        for col, tipo in colunas_extras:
            try:
                cursor.execute(f"ALTER TABLE personagens ADD COLUMN {col} {tipo}")
            except sqlite3.OperationalError:
                pass # Coluna já existe

        # --- CRIATURAS ---
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
        
        # --- HABILIDADES (Unificado) ---
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
        
        # --- INVENTÁRIO ---
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

        # --- ÍNDICES ---
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_personagens_user_id ON personagens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_user_id ON inventario(user_id)")
        
        conn.commit()