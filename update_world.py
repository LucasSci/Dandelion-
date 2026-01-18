import sqlite3

DB_NAME = "bestiario.db"

def update_world_db():
    print(f"🌍 Iniciando a criação do Mundo em {DB_NAME}...")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Atualizar Tabela de Personagens (Adicionar Coordenadas)
    try:
        cursor.execute("ALTER TABLE personagens ADD COLUMN localizacao_atual TEXT DEFAULT 'Novigrad'")
        cursor.execute("ALTER TABLE personagens ADD COLUMN coord_x INTEGER DEFAULT 450")
        cursor.execute("ALTER TABLE personagens ADD COLUMN coord_y INTEGER DEFAULT 300")
        print("✅ Colunas de localização adicionadas em 'personagens'.")
    except sqlite3.OperationalError:
        print("🔹 Colunas em 'personagens' já existem.")

    # 2. Atualizar Tabela de Quests (Local da Missão)
    try:
        cursor.execute("ALTER TABLE quests ADD COLUMN local_nome TEXT DEFAULT 'Desconhecido'")
        cursor.execute("ALTER TABLE quests ADD COLUMN coord_x INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE quests ADD COLUMN coord_y INTEGER DEFAULT 0")
        print("✅ Colunas de localização adicionadas em 'quests'.")
    except sqlite3.OperationalError:
        print("🔹 Colunas em 'quests' já existem.")

    # 3. Criar Tabela de Locais (O Conhecimento do Mundo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locais_mundo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        regiao TEXT,
        descricao_lore TEXT,
        lendas_locais TEXT,
        coord_x INTEGER,
        coord_y INTEGER,
        nivel_perigo INTEGER DEFAULT 1
    );
    """)
    
    # 4. Popular com Locais Canônicos (Coordenadas baseadas num mapa 1024x1024 imaginário)
    # Novigrad (Norte Central), Velen (Centro Pântano), Skellige (Oeste Ilhas), Kaer Morhen (Nordeste Distante)
    locais_iniciais = [
        (
            "Novigrad", "Rebânia", 
            "A maior cidade do norte, cheia de templos, espiões e fogueiras.", 
            "Dizem que o Fogo Eterno queima aqueles que escondem magia, mas os esgotos escondem reis do crime.",
            450, 300, 1
        ),
        (
            "Velen", "Terra de Ninguém", 
            "Pântanos devastados pela guerra, lar de bruxas e deserters.", 
            "As Senhoras da Floresta exigem orelhas como pagamento por proteção contra a Peste.",
            450, 500, 3
        ),
        (
            "Kaer Morhen", "Montanhas Azuis", 
            "A antiga fortaleza dos bruxos da Escola do Lobo, isolada e em ruínas.", 
            "O vento nas montanhas carrega os uivos dos bruxos que morreram no massacre.",
            800, 100, 5
        ),
        (
            "Skellige", "Ilhas", 
            "Arquipélago de clãs guerreiros, drakkars e gigantes de gelo.", 
            "O fantasma do Rei Bran navega em dias de neblina procurando seu sucessor.",
            150, 600, 4
        ),
        (
            "Deserto de Korath", "Zerrikania", 
            "Um mar de areia e sol escaldante, lar de escorpiões e miragens.", 
            "Quem segue as flores de cacto encontra a cidade perdida de Zerrikania.",
            800, 800, 5
        ),
        (
            "Toussaint", "Sul", 
            "A terra do vinho e do amor, protegida por cavaleiros errantes.", 
            "Dizem que uma Besta mata cavaleiros que quebram suas virtudes.",
            600, 900, 2
        )
    ]

    for nome, reg, lore, lenda, x, y, perigo in locais_iniciais:
        try:
            cursor.execute("""
                INSERT INTO locais_mundo (nome, regiao, descricao_lore, lendas_locais, coord_x, coord_y, nivel_perigo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nome, reg, lore, lenda, x, y, perigo))
            print(f"📍 Local mapeado: {nome}")
        except sqlite3.IntegrityError:
            pass # Já existe

    conn.commit()
    conn.close()
    print("\n✨ Cartografia concluída! O Dandelion agora conhece o mundo.")

if __name__ == "__main__":
    update_world_db()