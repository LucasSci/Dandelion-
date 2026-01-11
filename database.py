import sqlite3

DB_NAME = "bestiario.db"

def get_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_NAME)

def init_db():
    """
    Inicializa as tabelas principais do sistema.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabela Personagens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personagens (
                user_id INTEGER PRIMARY KEY,
                nome TEXT,
                raca TEXT,
                classe TEXT,
                nivel INTEGER DEFAULT 1,
                historia TEXT,
                imagem_url TEXT,
                ouro INTEGER DEFAULT 0
            )
        """)
        
        # --- CORREÇÃO DO ERRO ---
        # Tenta adicionar a coluna 'ouro' em bancos antigos que não a tenham.
        try:
            cursor.execute("ALTER TABLE personagens ADD COLUMN ouro INTEGER DEFAULT 0")
            print("✅ Coluna 'ouro' adicionada com sucesso.")
        except sqlite3.OperationalError:
            # Se der erro, é porque a coluna já existe, então ignoramos.
            pass
        # ------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS criaturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                descricao TEXT,
                fraquezas TEXT,
                imagem_url TEXT
            )
        """)

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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habilidades_disponiveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE,
                efeito TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slots_equipados (
                user_id INTEGER,
                numero_slot INTEGER,
                habilidade_id INTEGER,
                PRIMARY KEY (user_id, numero_slot)
            )
        """)
        
        conn.commit()