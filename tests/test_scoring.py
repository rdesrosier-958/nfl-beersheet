"""Guards on scoring rules and config."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nfl import config, scoring, teams  # noqa: E402


def test_config_files_parse():
    settings = config.settings()
    assert settings["teams"] == 10
    assert settings["draft_rounds"] == 13
    assert sum(settings["starters"].values()) == 9

    scores = config.scoring()
    assert scores["receiving"]["reception"] == 0.5
    assert scores["passing"]["yards_per_point"] == 0.04
    assert scores["rushing"]["yards_per_point"] == 0.10


def test_half_ppr_reception_value():
    line = scoring.score_offense(
        {"rec": 80.0, "rec_yd": 1000.0, "rec_td": 6.0},
        17,
    )
    assert line.components["rec"] == pytest.approx(40.0)
    assert line.components["rec_yd"] == pytest.approx(100.0)
    assert line.components["rec_td"] == pytest.approx(36.0)


def test_passing_touchdowns_and_interceptions():
    line = scoring.score_offense({"pass_td": 30.0, "pass_int": 10.0}, 17)
    assert line.components["pass_td"] == pytest.approx(120.0)
    assert line.components["int"] == pytest.approx(-20.0)


def test_dst_value_falls_as_points_allowed_rises():
    values = [
        scoring.score_defense(games=17, mean_points_allowed=pa).total
        for pa in (14, 18, 22, 26, 30)
    ]
    assert values == sorted(values, reverse=True)


def test_kicker_distance_scoring():
    long_fg = scoring.score_kicker(
        games=1,
        xp_made_per_game=0.0,
        fg_attempts_per_game=1.0,
        distance_mix={"under40": 0.0, "fg40_49": 0.0, "fg50_plus": 1.0},
        make_rates={"under40": 1.0, "fg40_49": 1.0, "fg50_plus": 1.0},
    )
    assert long_fg.total == pytest.approx(5.0)


@pytest.mark.parametrize("raw,expected", [
    ("KC", "KC"),
    ("kansas city", "KC"),
    ("LAR", "LAR"),
    ("la", "LAR"),
    ("lac", "LAC"),
])
def test_team_aliases(raw, expected):
    assert teams.canonical(raw) == expected
