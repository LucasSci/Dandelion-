import sqlite3

DB_NAME = "bestiario.db"


def get_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_NAME)


def init_db():
    """
    Inicializa as tabelas principais do sistema.
    Deve ser chamada apenas uma vez na inicialização do bot.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personagens (
                user_id INTEGER PRIMARY KEY,
                nome TEXT,
                raca TEXT,
                classe TEXT,
                nivel INTEGER DEFAULT 1,
                historia TEXT,
                imagem_url TEXT
            )
        """)

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

        


def garantir_coluna_imagem_criaturas():
    """
    Garante que a coluna imagem_url exista na tabela criaturas.
    Evita erro em bancos antigos.
    """
    try:
        with get_connection() as conn:
            conn.execute(
                "ALTER TABLE criaturas ADD COLUMN imagem_url TEXT"
            )
            conn.commit()
            print("✅ Coluna 'imagem_url' adicionada em criaturas.")
    except sqlite3.OperationalError:
        # Coluna já existe ou tabela ainda não foi criada
        pass
