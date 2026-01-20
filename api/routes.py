from __future__ import annotations

import random
from typing import List, Tuple

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from vtt_engine.grid_system import GridMap


router = APIRouter()
app = FastAPI(title="Witcher TTRPG Integration")
MAP_SCALE_METERS_PER_SQUARE = 2


class RollSkillRequest(BaseModel):
    stat: int
    skill: int


class RollSkillResponse(BaseModel):
    total: int
    rolls: List[int]


def roll_exploding_d10() -> Tuple[int, List[int]]:
    total = 0
    rolls: List[int] = []
    rolling = True
    while rolling:
        roll = random.randint(1, 10)
        rolls.append(roll)
        if roll == 10:
            total += roll
            continue
        if roll == 1:
            total -= roll
            continue
        total += roll
        rolling = False
    return total, rolls


@router.post("/roll_skill", response_model=None)
def roll_skill(payload: RollSkillRequest) -> RollSkillResponse:
    roll_total, rolls = roll_exploding_d10()
    total = roll_total + payload.stat + payload.skill
    return RollSkillResponse(total=total, rolls=rolls)


class CombatUpdateRequest(BaseModel):
    token_id: str
    position: Tuple[int, int]
    grid: List[List[int]]


class CombatUpdateResponse(BaseModel):
    token_id: str
    position: Tuple[int, int]
    terrain_cost: int


class GenerateMapRequest(BaseModel):
    width: int
    height: int
    biome: str
    clima: str | None = None
    seed: int | None = None
    grid_mode: str = "square"


class GenerateMapResponse(BaseModel):
    grid: List[List[int]]
    metadata: dict


@router.post("/combat_update", response_model=None)
def combat_update(payload: CombatUpdateRequest) -> CombatUpdateResponse:
    width = len(payload.grid[0]) if payload.grid else 0
    height = len(payload.grid)
    grid_map = GridMap(width=width, height=height, grid=payload.grid)
    x, y = payload.position
    cost = grid_map.terrain_cost(x, y) if grid_map.in_bounds(x, y) else 9999
    return CombatUpdateResponse(token_id=payload.token_id, position=payload.position, terrain_cost=cost)


@router.post("/generate_map", response_model=None)
def generate_map(payload: GenerateMapRequest) -> GenerateMapResponse:
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
    return GenerateMapResponse(grid=grid_map.grid, metadata=metadata)


app.include_router(router)
