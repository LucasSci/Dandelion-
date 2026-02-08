from __future__ import annotations

from typing import Any, List, Tuple

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.observability import add_span_event, instrument_app, start_internal_span
from vtt_engine.grid_system import GridMap
from witcher_rules import rolar_pericia
from witcher_rules import rolar_d10_explosivo


router = APIRouter()
app = FastAPI(title="Witcher TTRPG Integration")
instrument_app(app)
MAP_SCALE_METERS_PER_SQUARE = 2


class VTTEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for websocket in list(self.active_connections):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)


ws_manager = WebSocketManager()


class RollSkillRequest(BaseModel):
    stat: int
    skill: int


class RollSkillResponse(BaseModel):
    total: int
    rolls: List[int]


@router.post("/roll_skill", response_model=None)
def roll_skill(payload: RollSkillRequest) -> RollSkillResponse:
    with start_internal_span(
        "roll_skill",
        {"stat": payload.stat, "skill": payload.skill},
    ):
        result = rolar_pericia(stat=payload.stat, skill=payload.skill)
        add_span_event("roll_result", {"total": result.total})
        return RollSkillResponse(total=result.total, rolls=result.rolls)
    roll_total, rolls = rolar_d10_explosivo()
    total = roll_total + payload.stat + payload.skill
    return RollSkillResponse(total=total, rolls=rolls)


class CombatUpdateRequest(BaseModel):
    token_id: str
    position: Tuple[int, int]
    grid: List[List[int]]
    grid_mode: str = "square"
    scale_meters: float = 2.0


class CombatUpdateResponse(BaseModel):
    token_id: str
    position: Tuple[int, int]
    terrain_cost: int
    grid_mode: str
    scale_meters: float


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
    with start_internal_span("combat_update"):
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
        add_span_event("terrain_cost", {"cost": cost})
        return CombatUpdateResponse(
            token_id=payload.token_id,
            position=payload.position,
            terrain_cost=cost,
            grid_mode=grid_map.grid_mode,
            scale_meters=grid_map.scale_meters,
        )


@router.post("/vtt/event", response_model=None)
async def vtt_event(payload: VTTEvent) -> dict[str, str]:
    with start_internal_span("vtt_event", {"event_type": payload.event_type}):
        await ws_manager.broadcast({"event": payload.event_type, "data": payload.payload})
        return {"status": "ok"}


@router.websocket("/ws/vtt")
async def vtt_ws(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


class MapGenerateRequest(BaseModel):
    width: int
    height: int
    biome: str
    clima: str | None = None
    grid_mode: str = "square"
    scale_meters: float = 2.0
    seed: int | None = None


class MapGenerateResponse(BaseModel):
    grid: List[List[int]]
    biome: str
    clima: str | None
    grid_mode: str
    scale_meters: float


@router.post("/generate_map", response_model=None)
def generate_map(payload: MapGenerateRequest) -> MapGenerateResponse:
    with start_internal_span(
        "generate_map",
        {"biome": payload.biome, "grid_mode": payload.grid_mode},
    ):
        grid_map = GridMap(
            width=payload.width,
            height=payload.height,
            grid_mode=payload.grid_mode,
            scale_meters=payload.scale_meters,
        )
        grid_map.generate(
            biome=payload.biome,
            seed=payload.seed,
            clima=payload.clima,
            grid_mode=payload.grid_mode,
        )
        return MapGenerateResponse(
            grid=grid_map.grid,
            biome=payload.biome,
            clima=payload.clima,
            grid_mode=grid_map.grid_mode,
            scale_meters=grid_map.scale_meters,
        )


@router.post("/generate_map", response_model=None)
def generate_map(payload: GenerateMapRequest) -> GenerateMapResponse:
    with start_internal_span(
        "generate_map_legacy",
        {"biome": payload.biome, "grid_mode": payload.grid_mode},
    ):
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
