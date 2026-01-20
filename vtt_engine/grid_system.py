from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


TerrainGrid = List[List[int]]
GridMode = str


@dataclass
class NoiseGenerator:
    biome: str
    seed: int | None = None

    def generate(self, width: int, height: int) -> TerrainGrid:
        rng = random.Random(self.seed)
        probabilities = self._biome_probabilities()
        grid: TerrainGrid = []
        for _ in range(height):
            row = [rng.choices([0, 1, 2], weights=probabilities, k=1)[0] for _ in range(width)]
            grid.append(row)
        return grid

    def _biome_probabilities(self) -> List[int]:
        if self.biome == "Pântano":
            return [50, 20, 30]
        if self.biome == "Floresta":
            return [60, 30, 10]
        if self.biome == "Caverna":
            return [40, 50, 10]
        if self.biome == "Cidade":
            return [70, 25, 5]
        return [60, 25, 15]


@dataclass
class GridMap:
    width: int
    height: int
    grid: TerrainGrid = field(default_factory=list)
    biome: str | None = None
    clima: str | None = None
    scale_meters_per_square: int = 2
    grid_mode: GridMode = "square"

    def generate(self, biome: str, clima: str | None = None, seed: int | None = None) -> None:
    grid_type: str = "square"
    scale_meters: float = 2.0
    biome: str | None = None
    clima: str | None = None

    def generate(
        self,
        biome: str,
        seed: int | None = None,
        clima: str | None = None,
        grid_type: str | None = None,
    ) -> None:
        self.biome = biome
        self.clima = clima
        if grid_type:
            self.grid_type = grid_type
        generator = NoiseGenerator(biome=biome, seed=seed)
        self.grid = generator.generate(self.width, self.height)
        self.biome = biome
        self.clima = clima

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def terrain_cost(self, x: int, y: int) -> int:
        terrain = self.grid[y][x]
        if terrain == 1:
            return 9999
        if terrain == 2:
            return 2
        return 1

    def neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        if self.grid_mode == "hex":
            return self._hex_neighbors(x, y)
        return self._square_neighbors(x, y)

    def _square_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [(nx, ny) for nx, ny in candidates if self.in_bounds(nx, ny)]

    def _hex_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        # odd-r offset coordinates
        if y % 2 == 0:
            candidates = [
                (x - 1, y - 1),
                (x, y - 1),
                (x - 1, y),
                (x + 1, y),
                (x - 1, y + 1),
                (x, y + 1),
            ]
        else:
            candidates = [
                (x, y - 1),
                (x + 1, y - 1),
                (x - 1, y),
                (x + 1, y),
                (x, y + 1),
                (x + 1, y + 1),
            ]
        if self.grid_type == "hex":
            if y % 2 == 0:
                deltas = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
            else:
                deltas = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
        else:
            deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        candidates = [(x + dx, y + dy) for dx, dy in deltas]
        return [(nx, ny) for nx, ny in candidates if self.in_bounds(nx, ny)]


@dataclass
class Pathfinding:
    grid_map: GridMap

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        frontier: List[Tuple[int, Tuple[int, int]]] = []
        heapq.heappush(frontier, (0, start))
        came_from: Dict[Tuple[int, int], Tuple[int, int] | None] = {start: None}
        cost_so_far: Dict[Tuple[int, int], int] = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break

            for neighbor in self._neighbors(current):
                x, y = neighbor
                new_cost = cost_so_far[current] + self.grid_map.terrain_cost(x, y)
                if new_cost >= 9999:
                    continue
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self._heuristic(goal, neighbor)
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current

        return self._reconstruct_path(came_from, start, goal)

    def _neighbors(self, node: Tuple[int, int]) -> List[Tuple[int, int]]:
        x, y = node
        return self.grid_map.neighbors(x, y)

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> int:
        if self.grid_map.grid_mode == "hex":
            return self._hex_distance(a, b)
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        ax, ay = Pathfinding._offset_to_axial(a[0], a[1])
        bx, by = Pathfinding._offset_to_axial(b[0], b[1])
        return int((abs(ax - bx) + abs(ay - by) + abs((ax + ay) - (bx + by))) / 2)

    @staticmethod
    def _offset_to_axial(x: int, y: int) -> Tuple[int, int]:
        q = x - (y - (y & 1)) // 2
        r = y
        return q, r

    @staticmethod
    def _reconstruct_path(
        came_from: Dict[Tuple[int, int], Tuple[int, int] | None],
        start: Tuple[int, int],
        goal: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        if goal not in came_from:
            return []
        current = goal
        path = []
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        if path and path[0] == start:
            return path
        return []
