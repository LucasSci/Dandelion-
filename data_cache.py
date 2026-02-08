from async_lru import alru_cache


@alru_cache(maxsize=1)
async def get_world_location_names(db):
    async with db.execute("SELECT nome FROM world_locations ORDER BY nome") as cursor:
        rows = await cursor.fetchall()
    return [row[0] for row in rows]


@alru_cache(maxsize=128)
async def get_world_location_details(db, nome):
    async with db.execute(
        "SELECT descricao, biome, clima FROM world_locations WHERE nome = ?",
        (nome,),
    ) as cursor:
        return await cursor.fetchone()


@alru_cache(maxsize=1)
async def get_personagens_para_mencoes(db):
    async with db.execute("SELECT id, nome FROM personagens WHERE nome IS NOT NULL") as cursor:
        return await cursor.fetchall()


def clear_world_location_caches():
    get_world_location_names.cache_clear()
    get_world_location_details.cache_clear()


def clear_personagem_mencoes_cache():
    get_personagens_para_mencoes.cache_clear()
