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


def clear_world_location_caches():
    get_world_location_names.cache_clear()
    get_world_location_details.cache_clear()
