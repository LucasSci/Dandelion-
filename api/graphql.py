from __future__ import annotations

from typing import List, Optional, Tuple

import strawberry

from vtt_engine.grid_system import GridMap
from witcher_rules import rolar_pericia

MAP_SCALE_METERS_PER_SQUARE = 2


@strawberry.type
class RollSkillResult:
    total: int
    rolls: List[int]


@strawberry.type
class CombatUpdateResult:
    token_id: str
    position: Tuple[int, int]
    terrain_cost: int
    grid_mode: str
    scale_meters: float


@strawberry.type
class GenerateMapResult:
    grid: List[List[int]]
    metadata: strawberry.scalars.JSON


@strawberry.input
class RollSkillInput:
    stat: int
    skill: int


@strawberry.input
class CombatUpdateInput:
    token_id: str
    position: Tuple[int, int]
    grid: List[List[int]]
    grid_mode: str = "square"
    scale_meters: float = 2.0


@strawberry.input
class GenerateMapInput:
    width: int
    height: int
    biome: str
    clima: Optional[str] = None
    seed: Optional[int] = None
    grid_mode: str = "square"


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "ok"


@strawberry.type
class Mutation:
    @strawberry.mutation
    def roll_skill(self, payload: RollSkillInput) -> RollSkillResult:
        result = rolar_pericia(stat=payload.stat, skill=payload.skill)
        return RollSkillResult(total=result.total, rolls=result.rolls)

    @strawberry.mutation
    def combat_update(self, payload: CombatUpdateInput) -> CombatUpdateResult:
        width = len(payload.grid[0]) if payload.grid else 0
        height = len(payload.grid)
        grid_map = GridMap(
            width=width,
            height=height,
            grid=payload.grid,
            grid_mode=payload.grid_mode,
            scale_meters=payload.scale_meters,
        )
        x, y = payload.position
        cost = grid_map.terrain_cost(x, y) if grid_map.in_bounds(x, y) else 9999
        return CombatUpdateResult(
            token_id=payload.token_id,
            position=payload.position,
            terrain_cost=cost,
            grid_mode=grid_map.grid_mode,
            scale_meters=grid_map.scale_meters,
        )

    @strawberry.mutation
    def generate_map(self, payload: GenerateMapInput) -> GenerateMapResult:
        grid_map = GridMap(
            width=payload.width,
            height=payload.height,
            scale_meters_per_square=MAP_SCALE_METERS_PER_SQUARE,
            grid_mode=payload.grid_mode,
        )
        grid_map.generate(biome=payload.biome, clima=payload.clima, seed=payload.seed)
        metadata = {
            "biome": grid_map.biome,
            "clima": grid_map.clima,
            "scale_meters_per_square": grid_map.scale_meters_per_square,
            "grid_mode": grid_map.grid_mode,
        }
        return GenerateMapResult(grid=grid_map.grid, metadata=metadata)


schema = strawberry.Schema(query=Query, mutation=Mutation)
