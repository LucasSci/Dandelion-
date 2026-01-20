from __future__ import annotations

from typing import List, Tuple

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from vtt_engine.grid_system import GridMap
from witcher_rules import rolar_pericia
from witcher_rules import rolar_d10_explosivo


router = APIRouter()
app = FastAPI(title="Witcher TTRPG Integration")


class RollSkillRequest(BaseModel):
    stat: int
    skill: int


class RollSkillResponse(BaseModel):
    total: int
    rolls: List[int]


@router.post("/roll_skill", response_model=None)
def roll_skill(payload: RollSkillRequest) -> RollSkillResponse:
    result = rolar_pericia(stat=payload.stat, skill=payload.skill)
    return RollSkillResponse(total=result.total, rolls=result.rolls)
    roll_total, rolls = rolar_d10_explosivo()
    total = roll_total + payload.stat + payload.skill
    return RollSkillResponse(total=total, rolls=rolls)


class CombatUpdateRequest(BaseModel):
    token_id: str
    position: Tuple[int, int]
    grid: List[List[int]]
    grid_type: str = "square"
    scale_meters: float = 2.0


class CombatUpdateResponse(BaseModel):
    token_id: str
    position: Tuple[int, int]
    terrain_cost: int
    grid_type: str
    scale_meters: float


@router.post("/combat_update", response_model=None)
def combat_update(payload: CombatUpdateRequest) -> CombatUpdateResponse:
    width = len(payload.grid[0]) if payload.grid else 0
    height = len(payload.grid)
    grid_map = GridMap(
        width=width,
        height=height,
        grid=payload.grid,
        grid_type=payload.grid_type,
        scale_meters=payload.scale_meters,
    )
    x, y = payload.position
    cost = grid_map.terrain_cost(x, y) if grid_map.in_bounds(x, y) else 9999
    return CombatUpdateResponse(
        token_id=payload.token_id,
        position=payload.position,
        terrain_cost=cost,
        grid_type=grid_map.grid_type,
        scale_meters=grid_map.scale_meters,
    )


class MapGenerateRequest(BaseModel):
    width: int
    height: int
    biome: str
    clima: str | None = None
    grid_type: str = "square"
    scale_meters: float = 2.0
    seed: int | None = None


class MapGenerateResponse(BaseModel):
    grid: List[List[int]]
    biome: str
    clima: str | None
    grid_type: str
    scale_meters: float


@router.post("/generate_map", response_model=None)
def generate_map(payload: MapGenerateRequest) -> MapGenerateResponse:
    grid_map = GridMap(
        width=payload.width,
        height=payload.height,
        grid_type=payload.grid_type,
        scale_meters=payload.scale_meters,
    )
    grid_map.generate(
        biome=payload.biome,
        seed=payload.seed,
        clima=payload.clima,
        grid_type=payload.grid_type,
    )
    return MapGenerateResponse(
        grid=grid_map.grid,
        biome=payload.biome,
        clima=payload.clima,
        grid_type=grid_map.grid_type,
        scale_meters=grid_map.scale_meters,
    )


app.include_router(router)
