import re
import random

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