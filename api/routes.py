from __future__ import annotations

from typing import Any, List, Tuple

from fastapi import APIRouter, Depends, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter

from api.auth import require_api_key, validate_api_key
from api.graphql import schema
from api.rate_limit import rate_limiter
from vtt_engine.grid_system import GridMap
from witcher_rules import rolar_pericia


router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(require_api_key), Depends(rate_limiter)],
    tags=["v1"],
)
app = FastAPI(
    title="Witcher TTRPG Integration",
    version="1.0.0",
    description=(
        "REST e GraphQL para automações de VTT com autenticação por API key, "
        "versionamento e rate limiting."
    ),
)
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


@router.post("/roll_skill", response_model=RollSkillResponse)
def roll_skill(payload: RollSkillRequest) -> RollSkillResponse:
    result = rolar_pericia(stat=payload.stat, skill=payload.skill)
    return RollSkillResponse(total=result.total, rolls=result.rolls)


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


@router.post("/combat_update", response_model=CombatUpdateResponse)
def combat_update(payload: CombatUpdateRequest) -> CombatUpdateResponse:
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
    return CombatUpdateResponse(
        token_id=payload.token_id,
        position=payload.position,
        terrain_cost=cost,
        grid_mode=grid_map.grid_mode,
        scale_meters=grid_map.scale_meters,
    )


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
    metadata: dict


@router.post("/generate_map", response_model=MapGenerateResponse)
def generate_map(payload: MapGenerateRequest) -> MapGenerateResponse:
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
    return MapGenerateResponse(grid=grid_map.grid, metadata=metadata)


@router.post("/vtt/event", response_model=dict[str, str])
async def vtt_event(payload: VTTEvent) -> dict[str, str]:
    await ws_manager.broadcast({"event": payload.event_type, "data": payload.payload})
    return {"status": "ok"}


@router.websocket("/ws/vtt")
async def vtt_ws(websocket: WebSocket) -> None:
    api_key = (
        websocket.query_params.get("api_key")
        or websocket.headers.get("x-api-key")
        or websocket.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    try:
        validate_api_key(api_key)
    except Exception:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


graphql_router = GraphQLRouter(
    schema,
    dependencies=[Depends(require_api_key), Depends(rate_limiter)],
)

app.include_router(router)
app.include_router(graphql_router, prefix="/v1/graphql", tags=["graphql"])
