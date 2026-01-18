import sqlite3

DB_NAME = "bestiario.db"

def fix_database():
    print(f"🔧 Iniciando reparo no banco de dados: {DB_NAME}...")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Lista de colunas novas que precisamos garantir que existam na tabela 'quests'
        novas_colunas = [
            ("alvo_monstro_nome", "TEXT"),
            ("imagem_url", "TEXT"),
            ("criatura_id", "INTEGER"),
            ("regiao", "TEXT DEFAULT 'Desconhecida'"),
            ("max_jogadores", "INTEGER DEFAULT 4"),
            ("thread_id", "INTEGER"),
            ("classes_req", "TEXT DEFAULT 'Todas'")
        ]

        # Tenta adicionar cada coluna. Se já existir, o SQLite avisa e o script ignora.
        for coluna, tipo in novas_colunas:
            try:
                cursor.execute(f"ALTER TABLE quests ADD COLUMN {coluna} {tipo}")
                print(f"✅ Coluna '{coluna}' adicionada com sucesso!")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"🔹 Coluna '{coluna}' já existe (Ignorado).")
                else:
                    print(f"❌ Erro ao adicionar '{coluna}': {e}")

        # Garante que a tabela de memória existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoria_campanha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            conteudo TEXT,
            data_registro TEXT DEFAULT (datetime('now'))
        );
        """)
        print("✅ Tabela 'memoria_campanha' verificada.")
        
        # Garante que a tabela de participantes existe
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quest_participantes (
            quest_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY(quest_id) REFERENCES quests(id) ON DELETE CASCADE,
            PRIMARY KEY(quest_id, user_id)
        );
        """)
        print("✅ Tabela 'quest_participantes' verificada.")

        conn.commit()
        conn.close()
        print("\n✨ Reparo concluído! Reinicie o bot agora.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    fix_database()