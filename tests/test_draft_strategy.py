"""Tests for bye weeks and draft strategy tabs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nfl import bye_weeks, config, draft_strategy, value  # noqa: E402
from nfl.records import Projection  # noqa: E402
from nfl.players import Player  # noqa: E402


def test_bye_weeks_cover_all_teams():
    assert len(bye_weeks.BYE_WEEK_2026) == 32
    assert bye_weeks.for_team("KC") == 5
    assert bye_weeks.for_team("kansas city chiefs") == 5
    assert bye_weeks.teams_on_bye(11) == ("ATL", "CLE", "GB", "LAR", "NE", "SEA")


def test_draft_strategy_rows_espn():
    config.set_league("espn-half-ppr")
    board = _sample_board()
    rows = draft_strategy.build_rows(board)
    assert rows[0][0] == "DRAFT STRATEGY"
    assert any(row[0] == "BYE WEEK PLANNING" for row in rows)
    assert any(row[0] == "Week 11" for row in rows)


def test_draft_strategy_rows_yahoo():
    config.set_league("yahoo-full-ppr")
    board = _sample_board()
    rows = draft_strategy.build_rows(board)
    assert any("full PPR" in row[1] for row in rows if len(row) > 1)
    assert any(row[0] == "Rounds 1–3" for row in rows)


def _sample_board() -> value.Board:
    players = [
        Projection(
            player=Player("Jahmyr Gibbs", "RB", "DET", "jahmyr gibbs"),
            position="RB", team="DET", games=17, stats={}, points=330, per_game=19.4,
            components={}, projection_basis="test",
        ),
        Projection(
            player=Player("Ja'Marr Chase", "WR", "CIN", "jamarr chase"),
            position="WR", team="CIN", games=17, stats={}, points=280, per_game=16.5,
            components={}, projection_basis="test", bye=10,
        ),
    ]
    board = value.build(players)
    assert board.players
    return board
