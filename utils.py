import re
import random

from witcher_rules import rolar_d10_explosivo

def rolar_dados(formula: str):
    """
    Rola dados baseados em string ex: '1d20+5' ou '2d6'.
    Retorna (detalhes_str, valor_total_int).
    """
    if not formula:
        return None, 0
        
    formula = formula.lower().replace(" ", "")
    # Tenta encontrar padrão XdY+Z
    match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', formula)
    
    if not match:
        # Se for apenas um número fixo (ex: "5")
        if formula.isdigit():
            return f"[{formula}]", int(formula)
        return None, 0
    
    qtd, lados, sinal, bonus = match.groups()
    qtd, lados = int(qtd), int(lados)
    bonus = int(bonus) if bonus else 0
    
    rolls = [random.randint(1, lados) for _ in range(qtd)]
    total = sum(rolls) + (bonus if sinal == "+" else -bonus)
    
    detalhes = f"[{', '.join(map(str, rolls))}]"
    if bonus: detalhes += f" {'+' if sinal=='+' else '-'} {bonus}"
    
    return detalhes, total

def rolar_pericia_explosiva(stat: int, skill: int):
    """
    Rola 1d10 com explosão para cima (10) ou para baixo (1).
    Retorna (lista_de_rolagens, total, direcao_explosao).
    direcao_explosao: 1 (cima), -1 (baixo) ou 0 (sem explosão).
    """
    total_d10, rolagens = rolar_d10_explosivo(roller=random.randint)
    direcao = 0
    if rolagens:
        if rolagens[0] == 10:
            direcao = 1
        elif rolagens[0] == 1:
            direcao = -1

    total = total_d10 + stat + skill
    return rolagens, total, direcao

def calcular_xp_necessario(nivel_atual):
    # Fórmula: Base 100 * (Nível ^ 2) * Constante de ajuste
    # Exemplo simples estilo D&D:
    tabela = {
        1: 300, 2: 900, 3: 2700, 4: 6500, 5: 14000,
        6: 23000, 7: 34000, 8: 48000, 9: 64000, 10: 85000
    }
    return tabela.get(nivel_atual, nivel_atual * 10000) # Fallback para níveis altos

async def adicionar_xp(db, user_id, xp_ganho, channel):
    async with db.execute("SELECT nivel, xp_atual, hp_max, ataque FROM personagens WHERE user_id = ?", (user_id,)) as cursor:
        dados = await cursor.fetchone()
    
    if not dados: return
    nivel, xp, hp, atk = dados
    
    novo_xp = xp + xp_ganho
    xp_req = calcular_xp_necessario(nivel)
    
    msg = f"🌟 Ganhou **{xp_ganho} XP**!"
    
    # Check de Level Up
    if novo_xp >= xp_req:
        novo_nivel = nivel + 1
        novo_xp = novo_xp - xp_req # O que sobra vai para o próximo (ou zera, depende do seu gosto)
        
        # Bônus de Atributos (Exemplo)
        novo_hp = hp + 10
        novo_atk = atk + 1
        
        await db.execute("""
            UPDATE personagens 
            SET nivel = ?, xp_atual = ?, hp_max = ?, ataque = ? 
            WHERE user_id = ?
        """, (novo_nivel, novo_xp, novo_hp, novo_atk, user_id))
        
        msg += f"\n🎉 **LEVEL UP!** Você alcançou o nível **{novo_nivel}**!\n(+10 HP, +1 ATK)"
    else:
        await db.execute("UPDATE personagens SET xp_atual = ? WHERE user_id = ?", (novo_xp, user_id))
    
    await db.commit()
    await channel.send(msg)
