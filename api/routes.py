from __future__ import annotations

from typing import List, Tuple

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from vtt_engine.grid_system import GridMap
from witcher_rules import rolar_pericia


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


class CombatUpdateRequest(BaseModel):
    token_id: str
    position: Tuple[int, int]
    grid: List[List[int]]


class CombatUpdateResponse(BaseModel):
    token_id: str
    position: Tuple[int, int]
    terrain_cost: int


@router.post("/combat_update", response_model=None)
def combat_update(payload: CombatUpdateRequest) -> CombatUpdateResponse:
    width = len(payload.grid[0]) if payload.grid else 0
    height = len(payload.grid)
    grid_map = GridMap(width=width, height=height, grid=payload.grid)
    x, y = payload.position
    cost = grid_map.terrain_cost(x, y) if grid_map.in_bounds(x, y) else 9999
    return CombatUpdateResponse(token_id=payload.token_id, position=payload.position, terrain_cost=cost)


app.include_router(router)
