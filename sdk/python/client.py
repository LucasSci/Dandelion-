from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


@dataclass
class DandelionClient:
    base_url: str = "http://localhost:8000"
    api_key: str = "dev-secret"

    def _request(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        data = json.dumps(payload or {}).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
            },
            method="POST",
        )
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def roll_skill(self, *, stat: int, skill: int) -> Dict[str, Any]:
        return self._request("/v1/roll_skill", {"stat": stat, "skill": skill})

    def combat_update(
        self,
        *,
        token_id: str,
        position: tuple[int, int],
        grid: list[list[int]],
        grid_mode: str = "square",
        scale_meters: float = 2.0,
    ) -> Dict[str, Any]:
        return self._request(
            "/v1/combat_update",
            {
                "token_id": token_id,
                "position": list(position),
                "grid": grid,
                "grid_mode": grid_mode,
                "scale_meters": scale_meters,
            },
        )

    def generate_map(
        self,
        *,
        width: int,
        height: int,
        biome: str,
        clima: Optional[str] = None,
        seed: Optional[int] = None,
        grid_mode: str = "square",
    ) -> Dict[str, Any]:
        return self._request(
            "/v1/generate_map",
            {
                "width": width,
                "height": height,
                "biome": biome,
                "clima": clima,
                "seed": seed,
                "grid_mode": grid_mode,
            },
        )

    def vtt_event(self, *, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("/v1/vtt/event", {"event_type": event_type, "payload": payload})

    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("/v1/graphql", {"query": query, "variables": variables or {}})
