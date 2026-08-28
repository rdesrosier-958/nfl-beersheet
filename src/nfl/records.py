"""Shared record types."""

from __future__ import annotations

from dataclasses import dataclass, field

from .players import Player


@dataclass
class Projection:
    player: Player
    position: str
    team: str
    games: float
    stats: dict[str, float]
    points: float
    per_game: float
    components: dict[str, float] = field(default_factory=dict)
    projection_basis: str = ""
    market_rank: float | None = None
    market_pos_rank: float | None = None
    market_sources: int = 0
    subvertadown_val: float | None = None
    subvertadown_adp: float | None = None
    bye: int | None = None
    notes: str = ""

    @property
    def name(self) -> str:
        return self.player.name
