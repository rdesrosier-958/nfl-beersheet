"""Turn projected points into draft value (VOLS + BEER)."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from . import config
from .records import Projection

DEFAULT_BENCH_ALLOCATION = {"QB": 15, "RB": 25, "WR": 25, "TE": 8, "K": 2, "DST": 2}
DRAFTABLE_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
DEFAULT_FLOOR_PER_TEAM = {
    "QB": 1.75,
    "RB": 4.25,
    "WR": 4.25,
    "TE": 1.75,
    "K": 1.25,
    "DST": 1.25,
}


def bench_allocation() -> dict[str, int]:
    return config.model().get("bench_allocation", DEFAULT_BENCH_ALLOCATION)


@dataclass
class Valued:
    projection: Projection
    position_rank: int
    value: float
    vols: float
    beer: float
    tier: int
    value_rank: int = 0
    board_rank: float | None = None
    board_pos_rank: float | None = None
    board_delta: float | None = None
    target_round: int = 0

    @property
    def name(self) -> str:
        return self.projection.name

    @property
    def position(self) -> str:
        return self.projection.position

    @property
    def team(self) -> str:
        return self.projection.team

    @property
    def points(self) -> float:
        return self.projection.points


@dataclass
class Board:
    players: list[Valued]
    starter_demand: dict[str, int] = field(default_factory=dict)
    vols_baseline: dict[str, float] = field(default_factory=dict)
    beer_baseline: dict[str, float] = field(default_factory=dict)
    flex_allocation: dict[str, int] = field(default_factory=dict)

    def by_position(self, position: str) -> list[Valued]:
        return [p for p in self.players if p.position == position]


def starter_demand(by_position: dict[str, list[Projection]]) -> tuple[dict[str, int], dict[str, int]]:
    settings = config.settings()
    teams = settings["teams"]
    starters = settings["starters"]
    flex_map = settings["flex"]

    demand = {
        position: count * teams
        for position, count in starters.items()
        if position not in flex_map
    }
    demand.setdefault("TE", 0)

    allocation = {position: 0 for position in ("RB", "WR", "TE")}
    for flex_name, eligible in flex_map.items():
        slots = starters[flex_name] * teams
        for _ in range(slots):
            best_position, best_points = None, float("-inf")
            for position in eligible:
                pool = by_position.get(position, [])
                index = demand.get(position, 0) + allocation[position]
                if index < len(pool) and pool[index].points > best_points:
                    best_position, best_points = position, pool[index].points
            if best_position is None:
                break
            allocation[best_position] += 1

    for position, extra in allocation.items():
        demand[position] = demand.get(position, 0) + extra
    return demand, allocation


def _baseline(pool: list[Projection], index: int) -> float:
    if not pool:
        return 0.0
    position = min(max(index, 1), len(pool)) - 1
    return pool[position].points


def build(projections: list[Projection]) -> Board:
    by_position: dict[str, list[Projection]] = {}
    for projection in projections:
        by_position.setdefault(projection.position, []).append(projection)
    for pool in by_position.values():
        pool.sort(key=lambda p: -p.points)

    demand, allocation = starter_demand(by_position)
    gaps = config.model()["tier_gap_points"]

    vols_baseline: dict[str, float] = {}
    beer_baseline: dict[str, float] = {}
    for position, pool in by_position.items():
        starters = demand.get(position, len(pool))
        vols_baseline[position] = _baseline(pool, starters)
        beer_baseline[position] = _baseline(pool, starters + bench_allocation().get(position, 2))

    valued: list[Valued] = []
    for position, pool in by_position.items():
        tier, previous = 1, None
        gap = gaps.get(position, 10)
        for index, projection in enumerate(pool, start=1):
            if previous is not None and (previous - projection.points) > gap:
                tier += 1
            previous = projection.points
            vols = projection.points - vols_baseline[position]
            beer = projection.points - beer_baseline[position]
            delta = (
                projection.market_pos_rank - index
                if projection.market_pos_rank is not None else None
            )
            valued.append(Valued(
                projection=projection, position_rank=index,
                value=(vols + beer) / 2, vols=vols, beer=beer, tier=tier,
                board_rank=projection.market_rank,
                board_pos_rank=projection.market_pos_rank,
                board_delta=delta,
            ))

    valued.sort(key=lambda v: -v.value)
    teams = config.settings()["teams"]
    for index, entry in enumerate(valued, start=1):
        entry.value_rank = index
        entry.target_round = (index + teams - 1) // teams

    return Board(
        players=valued, starter_demand=demand,
        vols_baseline=vols_baseline, beer_baseline=beer_baseline,
        flex_allocation=allocation,
    )


def total_picks() -> int:
    settings = config.settings()
    return settings["teams"] * settings["draft_rounds"]


def draftable_floors(board: Board) -> dict[str, int]:
    """League-wide minimum names per position on the Draftable tab."""
    teams = config.settings()["teams"]
    per_team = config.model().get("draftable_floor_per_team", DEFAULT_FLOOR_PER_TEAM)
    floors: dict[str, int] = {}
    for position in DRAFTABLE_POSITIONS:
        rate = per_team.get(position, 1.0)
        floors[position] = math.ceil(teams * rate)
    return floors


def draftable(board: Board) -> list[Valued]:
    depth = int(round(total_picks() * config.model()["draft_cushion"]))
    floors = draftable_floors(board)
    chosen: dict[tuple[str, str], Valued] = {
        (entry.name, entry.position): entry for entry in board.players[:depth]
    }

    counts = Counter(entry.position for entry in chosen.values())
    for position, floor in floors.items():
        missing = floor - counts.get(position, 0)
        if missing <= 0:
            continue
        for entry in board.by_position(position):
            key = (entry.name, entry.position)
            if key in chosen:
                continue
            chosen[key] = entry
            missing -= 1
            if missing <= 0:
                break

    return sorted(chosen.values(), key=lambda entry: entry.value_rank)


def snake_picks(slot: int) -> list[int]:
    settings = config.settings()
    teams, rounds = settings["teams"], settings["draft_rounds"]
    picks = []
    for rnd in range(1, rounds + 1):
        position = slot if rnd % 2 == 1 else teams - slot + 1
        picks.append((rnd - 1) * teams + position)
    return picks
