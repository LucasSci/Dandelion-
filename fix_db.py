import sqlite3

DB_NAME = "bestiario.db"

def fix_regions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("🌍 Atualizando Atlas do Mundo...")

    # 1. Inserir Zerrikania explicitamente se não existir
    # Note as coordenadas (900, 850) - Extremo Sudeste do mapa
    try:
        cursor.execute("""
            INSERT INTO locais_mundo (nome, regiao, descricao_lore, lendas_locais, coord_x, coord_y, nivel_perigo)
            VALUES (
                'Zerrikania', 
                'Terras do Leste', 
                'A terra dos dragões, guerreiras tatuadas e alquimia exótica. Um lugar de calor escaldante e mistérios antigos.',
                'Dizem que o culto ao Dragão Dourado guarda tesouros nas areias profundas.',
                900, 850, 5
            )
        """)
        print("✅ Zerrikania adicionada ao mapa.")
    except sqlite3.IntegrityError:
        print("🔹 Zerrikania já consta nos registros.")

    # 2. Atualizar Deserto de Korath para pertencer à região de Zerrikania (opcional, para consistência)
    cursor.execute("UPDATE locais_mundo SET regiao = 'Zerrikania' WHERE nome = 'Deserto de Korath'")
    
    conn.commit()
    conn.close()
    print("✨ Atlas atualizado!")

if __name__ == "__main__":
    fix_regions()