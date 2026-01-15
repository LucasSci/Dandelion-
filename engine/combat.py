# Helper de XP e Nível
async def processar_xp(db, user_id, xp_ganho, channel):
    async with db.execute("SELECT nivel, xp_atual, hp_max, ataque FROM personagens WHERE user_id = ?", (user_id,)) as cursor:
        dados = await cursor.fetchone()
    
    if not dados: return
    nivel, xp, hp, atk = dados
    
    # Fórmula: Nível * 1000 (Ex: Nvl 1 precisa de 1000xp para virar 2)
    xp_prox_nivel = nivel * 1000 
    novo_xp = xp + xp_ganho
    msg = ""

    if novo_xp >= xp_prox_nivel:
        novo_nivel = nivel + 1
        novo_xp = novo_xp - xp_prox_nivel
        novo_hp = hp + 5   # Ganha 5 HP
        novo_atk = atk + 1 # Ganha 1 Atk
        
        await db.execute("UPDATE personagens SET nivel=?, xp_atual=?, hp_max=?, ataque=? WHERE user_id=?", 
                         (novo_nivel, novo_xp, novo_hp, novo_atk, user_id))
        msg = f"\n🎉 **LEVEL UP!** Você alcançou o nível **{novo_nivel}**! (+5 HP, +1 ATK)"
    else:
        await db.execute("UPDATE personagens SET xp_atual=? WHERE user_id=?", (novo_xp, user_id))
    
    await db.commit()
    if msg: await channel.send(f"<@{user_id}> {msg}")