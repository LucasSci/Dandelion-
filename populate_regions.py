import sqlite3

DB_NAME = "bestiario.db"

def popular_mundo():
    print("🌍 Mapeando o Continente...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Lista completa de regiões com Lore para a IA (Evita erros como pântano no deserto)
    atlas_mundial = [
        (
            "Novigrad", "Norte (Redania)", 
            "GEOGRAFIA: A maior cidade do norte. Urbana, portuária, ruas de pedra, canais e esgotos. Clima temperado.\nCULTURA: Comércio, crime organizado, Igreja do Fogo Eterno, perseguição a magos.\nPROBLEMAS: Espionagem, assassinos, doppelgangers, caçadores de bruxas.",
            "O Fogo Eterno protege a cidade, mas as sombras pertencem aos Reis do Crime."
        ),
        (
            "Velen", "Terra de Ninguém", 
            "GEOGRAFIA: Pântanos lamacentos, florestas mortas, campos de batalha e aldeias miseráveis. Clima chuvoso e cinzento.\nCULTURA: Camponeses supersticiosos, fome, guerra e adoração às Senhoras da Floresta.\nPROBLEMAS: Necrófagos, pragas, canibalismo, desertores, bruxas do pântano.",
            "Quem entra no Pântano Retorcido nunca mais volta o mesmo."
        ),
        (
            "Skellige", "Ilhas do Oeste", 
            "GEOGRAFIA: Arquipélago de montanhas geladas, fiordes e mar tempestuoso. Clima frio e neve.\nCULTURA: Vikings, clãs guerreiros, honra, navegação e druidas.\nPROBLEMAS: Gigantes de gelo, sereias, piratas, disputas de sucessão.",
            "O herói Hemdall vigia a ponte do arco-íris contra o fim dos tempos."
        ),
        (
            "Kaer Morhen", "Montanhas Azuis", 
            "GEOGRAFIA: Fortaleza isolada no topo de montanhas inacessíveis. Florestas de pinheiros e vales rochosos.\nCULTURA: Lar dos Bruxeiros da Escola do Lobo. Melancolia e ruínas.\nPROBLEMAS: Elementais, harpias, trolls e o isolamento total.",
            "O castelo guarda os segredos da Mutação, agora perdidos."
        ),
        (
            "Toussaint", "Sul (Nilfgaard)", 
            "GEOGRAFIA: O ducado do vinho. Colinas verdes ensolaradas, castelos de contos de fadas e lagos azuis.\nCULTURA: Cavalaria, torneios, etiqueta, vampiros disfarçados na alta sociedade.\nPROBLEMAS: Monstros que atacam vinhedos, maldições antigas, intriga da corte.",
            "Sob a beleza dos vinhedos, vampiros antigos dormem."
        ),
        (
            "Zerrikania", "Leste Distante", 
            "GEOGRAFIA: Deserto vasto, dunas de areia, cânions de pedra vermelha e oásis raros. Calor extremo.\nCULTURA: Culto aos Dragões, guerreiras tatuadas, alquimia exótica e isolacionismo.\nPROBLEMAS: Escorpiões gigantes, tempestades de areia, basiliscos, djins.",
            "Zerrikanterment, o Dragão Dourado, é adorado como um deus vivo."
        ),
        (
            "Ofir", "Além Mar", 
            "GEOGRAFIA: Terras exóticas além do mar, estepes e cidades de mármore branco.\nCULTURA: Mercadores ricos, magos das areias, cavalos velozes e runas avançadas.\nPROBLEMAS: Djins rebeldes, príncipes sapos, magia proibida.",
            "Os ventos de Ofir trazem magia que o Norte desconhece."
        ),
        (
            "Brokilon", "Floresta Antiga", 
            "GEOGRAFIA: Floresta densa e primordial, árvores gigantescas e musgo verde eterno.\nCULTURA: Dríades xenófobas que matam invasores. Matriarcal e protetora da natureza.\nPROBLEMAS: Invasões humanas, monstros vegetais, centopéias gigantes.",
            "A flecha de uma dríade nunca erra o olho de um humano."
        )
    ]

    for nome, regiao, lore, lenda in atlas_mundial:
        # Tenta inserir ou atualizar se já existir (Upsert manual)
        cursor.execute("SELECT id FROM locais_mundo WHERE nome = ?", (nome,))
        data = cursor.fetchone()
        
        if data:
            # Atualiza para garantir que a lore esteja correta (para a IA não errar)
            cursor.execute("""
                UPDATE locais_mundo 
                SET regiao=?, descricao_lore=?, lendas_locais=? 
                WHERE nome=?
            """, (regiao, lore, lenda, nome))
            print(f"🔄 Região atualizada: {nome}")
        else:
            # Insere nova
            cursor.execute("""
                INSERT INTO locais_mundo (nome, regiao, descricao_lore, lendas_locais, coord_x, coord_y) 
                VALUES (?, ?, ?, ?, 0, 0)
            """, (nome, regiao, lore, lenda))
            print(f"✅ Região descoberta: {nome}")

    conn.commit()
    conn.close()
    print("\n✨ Mapa Mundi Completo! Reinicie o bot e use /quest_gerar.")

if __name__ == "__main__":
    popular_mundo()