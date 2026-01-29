from __future__ import annotations

from typing import Iterable, Optional, Sequence


class CharacterRepository:
    def __init__(self, db):
        self.db = db

    async def list_available_names(self, current: str) -> list[tuple[str]]:
        async with self.db.execute(
            "SELECT nome FROM personagens WHERE user_id IS NULL AND nome LIKE ? LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            return await cursor.fetchall()

    async def list_user_names(self, user_id: int, current: str) -> list[tuple[str]]:
        async with self.db.execute(
            "SELECT nome FROM personagens WHERE user_id = ? AND nome LIKE ? LIMIT 25",
            (user_id, f"%{current}%"),
        ) as cursor:
            return await cursor.fetchall()

    async def list_all_names(self, current: str) -> list[tuple[str]]:
        async with self.db.execute(
            "SELECT nome FROM personagens WHERE nome LIKE ? LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            return await cursor.fetchall()

    async def list_location_names(self, current: str) -> list[tuple[str]]:
        async with self.db.execute(
            "SELECT nome FROM world_locations WHERE nome LIKE ? ORDER BY nome LIMIT 25",
            (f"%{current}%",),
        ) as cursor:
            return await cursor.fetchall()

    async def fetch_character_summary_by_user(self, user_id: int) -> Optional[tuple[int, str, int, int]]:
        async with self.db.execute(
            "SELECT id, nome, hp_atual, hp_max FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_progress_by_user(self, user_id: int) -> Optional[tuple[int, int, int, int, int]]:
        async with self.db.execute(
            "SELECT nivel, xp_atual, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_level_stats_by_user(self, user_id: int) -> Optional[tuple[int, int, int, int]]:
        async with self.db.execute(
            "SELECT nivel, hp_max, hp_atual, ataque FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def update_progress(
        self, user_id: int, nivel: int, xp_atual: int, hp_max: int, hp_atual: int, ataque: int
    ) -> None:
        await self.db.execute(
            """
            UPDATE personagens
            SET nivel=?, xp_atual=?, hp_max=?, hp_atual=?, ataque=?
            WHERE user_id=?
            """,
            (nivel, xp_atual, hp_max, hp_atual, ataque, user_id),
        )
        await self.db.commit()

    async def update_level_stats(self, user_id: int, nivel: int, hp_max: int, hp_atual: int, ataque: int) -> None:
        await self.db.execute(
            """
            UPDATE personagens SET nivel=?, hp_max=?, hp_atual=?, ataque=? WHERE user_id=?
            """,
            (nivel, hp_max, hp_atual, ataque, user_id),
        )
        await self.db.commit()

    async def fetch_gold_by_user(self, user_id: int) -> Optional[int]:
        async with self.db.execute(
            "SELECT ouro FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def update_gold_by_user(self, user_id: int, gold: int) -> None:
        await self.db.execute("UPDATE personagens SET ouro = ? WHERE user_id = ?", (gold, user_id))
        await self.db.commit()

    async def fetch_location_by_user(self, user_id: int) -> Optional[tuple[str, Optional[str]]]:
        async with self.db.execute(
            """
            SELECT p.nome, w.nome
            FROM personagens p
            LEFT JOIN world_locations w ON w.id = p.localizacao_id
            WHERE p.user_id = ?
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_location_id(self, destino: str) -> Optional[int]:
        async with self.db.execute("SELECT id FROM world_locations WHERE nome = ?", (destino,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def fetch_character_id_and_location(self, user_id: int) -> Optional[tuple[int, Optional[int]]]:
        async with self.db.execute(
            "SELECT id, localizacao_id FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def update_location(self, user_id: int, location_id: int) -> int:
        cursor = await self.db.execute(
            "UPDATE personagens SET localizacao_id = ? WHERE user_id = ?",
            (location_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount

    async def upsert_attribute(self, personagem_id: int, nome: str, valor: int) -> None:
        await self.db.execute(
            """
            INSERT INTO atributos_personagem (personagem_id, nome, valor)
            VALUES (?, ?, ?)
            ON CONFLICT(personagem_id, nome) DO UPDATE SET valor = excluded.valor
            """,
            (personagem_id, nome.strip(), valor),
        )
        await self.db.commit()

    async def list_attributes(self, personagem_id: int, limit: Optional[int] = None) -> list[tuple[str, int]]:
        query = "SELECT nome, valor FROM atributos_personagem WHERE personagem_id = ? ORDER BY nome"
        if limit:
            query += " LIMIT ?"
            params: Sequence[object] = (personagem_id, limit)
        else:
            params = (personagem_id,)

        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    @staticmethod
    def calculate_derived_stats(attributes: dict[str, int]) -> dict[str, int]:
        def _attr_value(key: str, default: int = 1) -> int:
            value = attributes.get(key, default)
            return default if value is None else int(value)

        body = _attr_value("BODY")
        will = _attr_value("WILL")
        ref = _attr_value("REF")
        dex = _attr_value("DEX")
        emp = _attr_value("EMP")

        return {
            "Stun": max(0, body + will),
            "Run": max(0, ref + dex),
            "Leap": max(0, body + dex),
            "HP": max(0, body * 5),
            "Stamina": max(0, body + will),
            "Vigor": max(0, body + will + emp),
            "Recovery": max(0, (body + will) // 2),
        }
    async def list_attributes_dict(self, personagem_id: int, limit: Optional[int] = None) -> dict[str, int]:
        attributes = await self.list_attributes(personagem_id, limit)
        return {nome: valor for nome, valor in attributes}

    async def upsert_armor(self, personagem_id: int, localizacao: str, sp: int) -> None:
        await self.db.execute(
            """
            INSERT INTO armaduras_personagem (personagem_id, localizacao, sp, reliability)
            VALUES (?, ?, ?, 100)
            ON CONFLICT(personagem_id, localizacao) DO UPDATE SET sp = excluded.sp
            """,
            (personagem_id, localizacao, sp),
        )
        await self.db.commit()

    async def fetch_armor(self, personagem_id: int, localizacao: str) -> Optional[tuple[int, int, Optional[int]]]:
        async with self.db.execute(
            "SELECT id, sp, reliability FROM armaduras_personagem WHERE personagem_id = ? AND localizacao = ?",
            (personagem_id, localizacao),
        ) as cursor:
            return await cursor.fetchone()

    async def create_armor(self, personagem_id: int, localizacao: str) -> int:
        cursor = await self.db.execute(
            """
            INSERT INTO armaduras_personagem (personagem_id, localizacao, sp, reliability)
            VALUES (?, ?, 0, 100)
            """,
            (personagem_id, localizacao),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def upsert_armor_modifier(self, armadura_id: int, tipo_dano: str, multiplicador: float) -> None:
        await self.db.execute(
            """
            INSERT INTO armadura_modificadores (armadura_id, tipo_dano, multiplicador)
            VALUES (?, ?, ?)
            ON CONFLICT(armadura_id, tipo_dano) DO UPDATE SET multiplicador = excluded.multiplicador
            """,
            (armadura_id, tipo_dano.strip().lower(), multiplicador),
        )
        await self.db.commit()

    async def fetch_armor_modifier(self, armadura_id: int, tipo_dano: str) -> Optional[float]:
        async with self.db.execute(
            "SELECT multiplicador FROM armadura_modificadores WHERE armadura_id = ? AND tipo_dano = ?",
            (armadura_id, tipo_dano.strip().lower()),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def update_armor_reliability(self, armadura_id: int, reliability: int) -> None:
        await self.db.execute(
            "UPDATE armaduras_personagem SET reliability = ? WHERE id = ?",
            (reliability, armadura_id),
        )
        await self.db.commit()

    async def update_hp(self, personagem_id: int, hp_atual: int) -> None:
        await self.db.execute(
            "UPDATE personagens SET hp_atual = ? WHERE id = ?",
            (hp_atual, personagem_id),
        )
        await self.db.commit()

    async def fetch_export_character(self, user_id: int) -> Optional[tuple]:
        async with self.db.execute(
            """
            SELECT id, nome, raca, classe, nivel, xp_atual, historia, imagem_url, ouro,
                   hp_max, hp_atual, mp_max, ataque, defesa, vigor_max, vigor_atual,
                   toxicidade_max, toxicidade_atual
            FROM personagens WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def list_armors(self, personagem_id: int, locations: Optional[Iterable[str]] = None) -> list[tuple[str, int, Optional[int]]]:
        if locations:
            locations_list = list(locations)
            placeholders = ",".join(["?"] * len(locations_list))
            query = (
                "SELECT localizacao, sp, reliability "
                "FROM armaduras_personagem "
                f"WHERE personagem_id = ? AND localizacao IN ({placeholders})"
            )
            params: Sequence[object] = (personagem_id, *locations_list)
        else:
            query = "SELECT localizacao, sp, reliability FROM armaduras_personagem WHERE personagem_id = ?"
            params = (personagem_id,)

        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def user_has_character(self, user_id: int) -> bool:
        async with self.db.execute("SELECT 1 FROM personagens WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None

    async def assign_character(self, user_id: int, nome_personagem: str) -> int:
        cursor = await self.db.execute(
            "UPDATE personagens SET user_id = ? WHERE nome = ? AND user_id IS NULL",
            (user_id, nome_personagem),
        )
        await self.db.commit()
        return cursor.rowcount

    async def release_character(self, user_id: int, nome_personagem: str) -> int:
        cursor = await self.db.execute(
            "UPDATE personagens SET user_id = NULL WHERE user_id = ? AND nome = ?",
            (user_id, nome_personagem),
        )
        await self.db.commit()
        return cursor.rowcount

    async def clear_user_character(self, user_id: int) -> None:
        await self.db.execute("UPDATE personagens SET user_id = NULL WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def assign_character_to_user(self, user_id: int, nome_personagem: str) -> int:
        cursor = await self.db.execute(
            "UPDATE personagens SET user_id = ? WHERE nome = ?",
            (user_id, nome_personagem),
        )
        await self.db.commit()
        return cursor.rowcount

    async def fetch_character_id_by_user(self, user_id: int) -> Optional[int]:
        async with self.db.execute(
            "SELECT id FROM personagens WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def list_characters(self, limit: int = 20) -> list[tuple[str, Optional[int]]]:
        limit = int(limit)
        async with self.db.execute(f"SELECT nome, user_id FROM personagens LIMIT {limit}") as cursor:
            return await cursor.fetchall()

    async def list_characters_filtered(
        self,
        raca: Optional[str] = None,
        classe: Optional[str] = None,
        genero: Optional[str] = None,
        limit: int = 20,
    ) -> list[tuple[str, Optional[int], Optional[str], Optional[str], Optional[str]]]:
        limit = int(limit)
        filtros = []
        params: list[object] = []
        if raca:
            filtros.append("LOWER(raca) LIKE ?")
            params.append(f"%{raca.strip().lower()}%")
        if classe:
            filtros.append("LOWER(classe) LIKE ?")
            params.append(f"%{classe.strip().lower()}%")
        if genero:
            filtros.append("LOWER(genero) LIKE ?")
            params.append(f"%{genero.strip().lower()}%")

        query = "SELECT nome, user_id, raca, classe, genero FROM personagens"
        if filtros:
            query += " WHERE " + " AND ".join(filtros)
        query += " LIMIT ?"
        params.append(limit)
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def fetch_embed_details(self, personagem_id: int) -> Optional[tuple]:
        async with self.db.execute(
            """
            SELECT p.nome, p.titulo, p.raca, p.classe, p.genero, p.nivel, p.historia, p.imagem_url, p.ouro,
                   p.hp_atual, p.hp_max, p.mp_max, p.ataque, p.defesa, p.xp_atual,
                   p.vigor_atual, p.vigor_max, p.toxicidade_atual, p.toxicidade_max, w.nome
            FROM personagens p
            LEFT JOIN world_locations w ON w.id = p.localizacao_id
            WHERE p.id = ?
            """,
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_identity(
        self, personagem_id: int
    ) -> Optional[tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
        async with self.db.execute(
            """
            SELECT nome, raca, classe, genero, imagem_url
            FROM personagens
            WHERE id = ?
            """,
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_profile(self, personagem_id: int) -> Optional[tuple[str, Optional[str], Optional[str]]]:
        async with self.db.execute(
            """
            SELECT nome, titulo, imagem_url
            FROM personagens
            WHERE id = ?
            """,
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_lore(self, personagem_id: int) -> Optional[tuple[str, Optional[str], Optional[str], Optional[str]]]:
        async with self.db.execute(
            """
            SELECT nome, titulo, historia, imagem_url
            FROM personagens
            WHERE id = ?
            """,
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_resources(self, personagem_id: int) -> Optional[tuple[int, int, int, int]]:
        async with self.db.execute(
            """
            SELECT p.vigor_atual, p.vigor_max, p.toxicidade_atual, p.toxicidade_max
            FROM personagens p
            WHERE p.id = ?
            """,
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_toxicity(self, personagem_id: int) -> Optional[tuple[int, int]]:
        async with self.db.execute(
            "SELECT toxicidade_atual, toxicidade_max FROM personagens WHERE id = ?",
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def update_toxicity(self, personagem_id: int, toxicidade_atual: int) -> None:
        await self.db.execute(
            "UPDATE personagens SET toxicidade_atual = ? WHERE id = ?",
            (toxicidade_atual, personagem_id),
        )
        await self.db.commit()

    async def fetch_vigor(self, personagem_id: int) -> Optional[tuple[int, int]]:
        async with self.db.execute(
            "SELECT vigor_atual, vigor_max FROM personagens WHERE id = ?",
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def update_vigor(self, personagem_id: int, vigor_atual: int) -> None:
        await self.db.execute(
            "UPDATE personagens SET vigor_atual = ? WHERE id = ?",
            (vigor_atual, personagem_id),
        )
        await self.db.commit()

    async def fetch_attack(self, personagem_id: int) -> Optional[int]:
        async with self.db.execute(
            "SELECT ataque FROM personagens WHERE id = ?",
            (personagem_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def fetch_combat_stats(self, personagem_id: int) -> Optional[tuple[int, int, int, int]]:
        async with self.db.execute(
            "SELECT hp_atual, hp_max, ataque, defesa FROM personagens WHERE id = ?",
            (personagem_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def fetch_level(self, personagem_id: int) -> Optional[int]:
        async with self.db.execute("SELECT nivel FROM personagens WHERE id = ?", (personagem_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None
