'''

Map generation module. Creates an 80x80 grid with a guaranteed path from start to door,
and populates it with monsters and chests.

'''

import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from entities import Monster
import constants as C


class MapData:
    def __init__(
        self,
        grid: List[List[int]],
        start: Tuple[int, int],
        door: Tuple[int, int],
        monsters: Dict[Tuple[int, int], Monster],
        chests: Set[Tuple[int, int]],
    ):
        self.grid = grid
        self.start = start
        self.door = door
        self.monsters = monsters
        self.chests = chests


def _neighbors(x: int, y: int, w: int, h: int):
    if x > 0:
        yield (x - 1, y)
    if x < w - 1:
        yield (x + 1, y)
    if y > 0:
        yield (x, y - 1)
    if y < h - 1:
        yield (x, y + 1)


def _bfs_has_path(grid: List[List[int]], start: Tuple[int, int], door: Tuple[int, int]) -> bool:
    w, h = len(grid[0]), len(grid)
    sx, sy = start
    gx, gy = door
    q = deque()
    q.append((sx, sy))
    seen = set([(sx, sy)])
    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy):
            return True
        for nx, ny in _neighbors(x, y, w, h):
            tile = grid[ny][nx]
            if tile != C.TILE_WALL and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return False


def _carve_path(grid: List[List[int]], start: Tuple[int, int], door: Tuple[int, int]):
    # Create a simple meandering but monotonic path from start to door
    x, y = start
    gx, gy = door
    grid[y][x] = C.TILE_FLOOR
    steps = 0
    max_steps = C.GRID_WIDTH * C.GRID_HEIGHT * 4
    while (x, y) != (gx, gy) and steps < max_steps:
        steps += 1
        moves = []
        if x < gx:
            moves.append((x + 1, y))
        elif x > gx:
            moves.append((x - 1, y))
        if y < gy:
            moves.append((x, y + 1))
        elif y > gy:
            moves.append((x, y - 1))

        # Occasionally add a perpendicular detour to make the path less straight
        if random.random() < 0.25:
            if random.random() < 0.5 and 1 <= y <= C.GRID_HEIGHT - 2:
                # move left/right randomly if within bounds
                if x > 1 and x < C.GRID_WIDTH - 2:
                    detour = (x + random.choice([-1, 1]), y)
                    moves.append(detour)
            else:
                if y > 1 and y < C.GRID_HEIGHT - 2:
                    detour = (x, y + random.choice([-1, 1]))
                    moves.append(detour)

        if not moves:
            break
        nx, ny = random.choice(moves)
        # clamp to inner bounds to avoid touching borders
        nx = min(max(1, nx), C.GRID_WIDTH - 2)
        ny = min(max(1, ny), C.GRID_HEIGHT - 2)
        x, y = nx, ny
        grid[y][x] = C.TILE_FLOOR

    # Ensure door tile is floor
    grid[gy][gx] = C.TILE_FLOOR


def _add_random_open_areas(grid: List[List[int]], density: float = 0.35, iterations: int = 3000):
    # Randomly carve more floors to create open areas
    for _ in range(iterations):
        if random.random() < density:
            x = random.randint(1, C.GRID_WIDTH - 2)
            y = random.randint(1, C.GRID_HEIGHT - 2)
            grid[y][x] = C.TILE_FLOOR
            # Bonus neighbors
            for nx, ny in _neighbors(x, y, C.GRID_WIDTH, C.GRID_HEIGHT):
                if random.random() < 0.2:
                    grid[ny][nx] = C.TILE_FLOOR


def generate_map(seed: Optional[int] = None) -> MapData:
    if seed is not None:
        random.seed(seed)
    # Initialize grid of walls
    grid = [[C.TILE_WALL for _ in range(C.GRID_WIDTH)] for _ in range(C.GRID_HEIGHT)]

    # Borders remain walls to keep player contained
    for x in range(C.GRID_WIDTH):
        grid[0][x] = C.TILE_WALL
        grid[C.GRID_HEIGHT - 1][x] = C.TILE_WALL
    for y in range(C.GRID_HEIGHT):
        grid[y][0] = C.TILE_WALL
        grid[y][C.GRID_WIDTH - 1] = C.TILE_WALL

    # Start and door positions
    start = (1, 1)
    door = (C.GRID_WIDTH - 2, C.GRID_HEIGHT - 2)

    # Carve a guaranteed path from start to door
    _carve_path(grid, start, door)

    # Carve more open areas
    _add_random_open_areas(grid, density=0.5, iterations=4000)

    # Place the door tile
    dx, dy = door
    grid[dy][dx] = C.TILE_DOOR

    # Verify connectivity; if fails, try again with a different seed offset
    attempts = 0
    while not _bfs_has_path(grid, start, door) and attempts < 5:
        attempts += 1
        _add_random_open_areas(grid, density=0.6, iterations=3000)

    # Place monsters and chests on floor tiles
    floor_positions = [(x, y) for y in range(C.GRID_HEIGHT) for x in range(C.GRID_WIDTH)
                       if grid[y][x] == C.TILE_FLOOR and (x, y) not in (start, door)]

    random.shuffle(floor_positions)

    # Heuristic counts based on available floor tiles
    num_monsters = max(40, min(200, len(floor_positions) // 20))
    num_chests = max(20, min(120, len(floor_positions) // 30))

    monsters: Dict[Tuple[int, int], Monster] = {}
    chests: Set[Tuple[int, int]] = set()

    # Place monsters
    placed = 0
    idx = 0
    while placed < num_monsters and idx < len(floor_positions):
        x, y = floor_positions[idx]
        idx += 1
        monsters[(x, y)] = Monster(x=x, y=y, hp=random.randint(C.MONSTER_HP_MIN, C.MONSTER_HP_MAX))
        grid[y][x] = C.TILE_MONSTER
        placed += 1

    # Place chests (avoid overlapping monsters)
    placed = 0
    while placed < num_chests and idx < len(floor_positions):
        x, y = floor_positions[idx]
        idx += 1
        if (x, y) not in monsters:
            grid[y][x] = C.TILE_CHEST
            chests.add((x, y))
            placed += 1

    return MapData(grid=grid, start=start, door=door, monsters=monsters, chests=chests)
