import sqlite3

DB_NAME = "bestiario.db"

def update_atlas():
    print("🌍 Ensinando Geografia e Cultura ao Dandelion...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Dicionário de Conhecimento: (Nome, Região Geral, Lore/Clima/Cultura, Lendas)
    atlas = [
        (
            "Zerrikania", "Leste Distante",
            "GEOGRAFIA: Um vasto deserto de areias douradas e cânions rochosos escaldantes. Clima árido e seco. Oásis raros e secretos.\nCULTURA: Matriarcal, guerreiras tatuadas que veneram dragões. Alquimia exótica (bombas e venenos). Isolacionistas.\nPROBLEMAS: Monstros do deserto (escorpiões gigantes, basiliscos), tempestades de areia mágicas, calor mortal.",
            "Dizem que o Dragão Dourado Zerrikanterment dorme sob as dunas e quem o acordar ganhará o fogo eterno."
        ),
        (
            "Velen", "Norte (Temeria)",
            "GEOGRAFIA: Pântanos úmidos, florestas mortas e lamaçal constante. Clima chuvoso e depressivo.\nCULTURA: Camponeses miseráveis devastados pela guerra. Superstição extrema e adoração a entidades pagãs (As Senhoras).\nPROBLEMAS: Canibalismo, pragas, deserters, necrófagos atraídos por cadáveres de guerra.",
            "As Senhoras da Floresta exigem orelhas como tributo para proteger as aldeias da Peste Catriona."
        ),
        (
            "Novigrad", "Norte (Redania)",
            "GEOGRAFIA: Metrópole portuária urbana, ruas de pedra, esgotos complexos e templos. Clima temperado.\nCULTURA: Cidade livre, racista contra não-humanos, controlada pela Igreja do Fogo Eterno e pelo Submundo do crime.\nPROBLEMAS: Caça às bruxas, espionagem, gangues rivais, monstros nos esgotos.",
            "O Fogo Eterno queima aqueles que escondem magia, mas dizem que o próprio Hierarca é um Doppler."
        ),
        (
            "Skellige", "Ilhas do Oeste",
            "GEOGRAFIA: Arquipélago montanhoso, fiordes gelados e mar tempestuoso. Clima frio e nevado.\nCULTURA: Clãs vikings, honra, saqueadores, banquetes e funerais no mar.\nPROBLEMAS: Gigantes de gelo, sereias atacando navios, disputas de sucessão entre clãs.",
            "O navio fantasma Naglfar, feito de unhas de mortos, navega na neblina trazendo o Ragh Nar Roog."
        ),
        (
            "Kaer Morhen", "Montanhas Azuis",
            "GEOGRAFIA: Vale isolado nas altas montanhas, cercado por picos nevados e florestas de pinheiros. Fortaleza em ruínas.\nCULTURA: Lar ancestral e solitário dos Bruxos da Escola do Lobo. Melancólico e vazio.\nPROBLEMAS: Elementais descontrolados, espectros de batalhas antigas, isolamento total.",
            "Os ventos uivam com as vozes dos bruxos mortos no massacre da fortaleza."
        ),
        (
            "Toussaint", "Sul (Nilfgaard)",
            "GEOGRAFIA: Colinas verdejantes, vinhedos ensolarados, lagos cristalinos e palácios de conto de fadas.\nCULTURA: Cavalaria andante, torneios, vinho, etiqueta da corte e segredos sombrios sob a beleza.\nPROBLEMAS: Vampiros, monstros que atacam vinhedos, maldições de contos de fadas distorcidos.",
            "Uma Besta mata cavaleiros que quebram as cinco virtudes da cavalaria."
        )
    ]

    for nome, regiao, lore, lenda in atlas:
        # Tenta atualizar se existir, ou inserir se não existir
        cursor.execute("SELECT id FROM locais_mundo WHERE nome = ?", (nome,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute("""
                UPDATE locais_mundo 
                SET descricao_lore = ?, lendas_locais = ?, regiao = ?
                WHERE nome = ?
            """, (lore, lenda, regiao, nome))
            print(f"🔄 Atualizado: {nome}")
        else:
            # Insere com coordenadas padrão (ajuste depois se precisar)
            cursor.execute("""
                INSERT INTO locais_mundo (nome, regiao, descricao_lore, lendas_locais, coord_x, coord_y)
                VALUES (?, ?, ?, ?, 0, 0)
            """, (nome, regiao, lore, lenda))
            print(f"🆕 Criado: {nome}")

    conn.commit()
    conn.close()
    print("✅ Banco de Dados Geográfico Sincronizado!")

if __name__ == "__main__":
    update_atlas()