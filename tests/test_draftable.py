"""Draftable tab depth and per-position floors."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nfl import config, value  # noqa: E402
from nfl.players import Player  # noqa: E402
from nfl.records import Projection  # noqa: E402


def _projection(name: str, position: str, team: str, points: float) -> Projection:
    return Projection(
        player=Player(name, position, team, name.lower()),
        position=position,
        team=team,
        games=17,
        stats={},
        points=points,
        per_game=points / 17,
        components={},
        projection_basis="test",
    )


def _board_with_depth() -> value.Board:
    players: list[Projection] = []
    points = 300.0
    for index in range(60):
        players.append(_projection(f"RB {index}", "RB", "NYJ", points - index))
    for index in range(70):
        players.append(_projection(f"WR {index}", "WR", "NYJ", points - 50 - index))
    for index in range(25):
        players.append(_projection(f"QB {index}", "QB", "NYJ", points - 100 - index))
    for index in range(25):
        players.append(_projection(f"TE {index}", "TE", "NYJ", points - 120 - index))
    for index in range(20):
        players.append(_projection(f"K {index}", "K", "NYJ", points - 140 - index))
    for index in range(20):
        players.append(_projection(f"DST {index}", "DST", "NYJ", points - 150 - index))
    return value.build(players)


@pytest.mark.parametrize(
    ("profile", "expected_floors"),
    [
        (
            "espn-half-ppr",
            {"QB": 18, "RB": 43, "WR": 43, "TE": 18, "K": 13, "DST": 13},
        ),
        (
            "yahoo-full-ppr",
            {"QB": 21, "RB": 54, "WR": 66, "TE": 21, "K": 15, "DST": 15},
        ),
    ],
)
def test_draftable_floors_from_league_config(profile, expected_floors):
    config.set_league(profile)
    board = _board_with_depth()
    assert value.draftable_floors(board) == expected_floors


@pytest.mark.parametrize("profile", ["espn-half-ppr", "yahoo-full-ppr"])
def test_draftable_meets_position_floors(profile):
    config.set_league(profile)
    board = _board_with_depth()
    floors = value.draftable_floors(board)
    draftable = value.draftable(board)
    counts = {}
    for entry in draftable:
        counts[entry.position] = counts.get(entry.position, 0) + 1
    for position, floor in floors.items():
        assert counts.get(position, 0) >= floor, (
            f"{profile} {position}: have {counts.get(position, 0)}, need {floor}"
        )
    assert len(draftable) >= int(round(value.total_picks() * config.model()["draft_cushion"]))
