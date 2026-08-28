"""Convert projected stat lines into ESPN half-PPR fantasy points."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.special import gammainc

from . import config


@dataclass
class ScoreBreakdown:
    total: float
    per_game: float
    components: dict[str, float] = field(default_factory=dict)


def score_offense(
    stats: dict[str, float],
    games: float,
    *,
    volatility: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Score a season stat line. `stats` holds season totals, not per-game."""
    s = config.scoring()
    games = max(games, 1.0)
    comp: dict[str, float] = {}

    comp["pass_yd"] = stats.get("pass_yd", 0.0) * s["passing"]["yards_per_point"]
    comp["pass_td"] = stats.get("pass_td", 0.0) * s["passing"]["td"]
    comp["int"] = stats.get("pass_int", 0.0) * s["passing"]["int"]
    comp["rush_yd"] = stats.get("rush_yd", 0.0) * s["rushing"]["yards_per_point"]
    comp["rush_td"] = stats.get("rush_td", 0.0) * s["rushing"]["td"]
    comp["rec"] = stats.get("rec", 0.0) * s["receiving"]["reception"]
    comp["rec_yd"] = stats.get("rec_yd", 0.0) * s["receiving"]["yards_per_point"]
    comp["rec_td"] = stats.get("rec_td", 0.0) * s["receiving"]["td"]
    comp["return_td"] = stats.get("return_td", 0.0) * s["returns"]["return_td"]

    total = sum(comp.values())
    return ScoreBreakdown(total, total / games, comp)


def volatility_for(position: str) -> dict[str, float]:
    v = config.model()["volatility"]
    if position == "QB":
        return {"pass": v["pass_yards"], "rush": v["rush_yards_qb"], "rec": v["rec_yards_wr"]}
    if position == "RB":
        return {"pass": v["pass_yards"], "rush": v["rush_yards_rb"], "rec": v["rec_yards_rb"]}
    if position == "TE":
        return {"pass": v["pass_yards"], "rush": v["rush_yards_wr"], "rec": v["rec_yards_te"]}
    return {"pass": v["pass_yards"], "rush": v["rush_yards_wr"], "rec": v["rec_yards_wr"]}


def _shutout_probability(mean_pa: float) -> float:
    if mean_pa <= 0:
        return 0.25
    return float(np.clip(0.30 * np.exp(-mean_pa / 9.0), 0.0, 0.25))


def expected_points_allowed_points(mean_pa: float, cv: float = 0.55) -> float:
    pa = config.scoring()["dst"]["points_allowed"]
    bands = pa["bands"]
    over_rate = pa["over_39_per_point"]

    if mean_pa <= 0:
        return float(bands[0]["points"])

    shape = 1.0 / (cv * cv)
    scale = mean_pa / shape

    def cdf(x: float) -> float:
        return float(gammainc(shape, x / scale))

    p_shutout = _shutout_probability(mean_pa)
    tail_mass = 1.0 - cdf(0.5)
    if tail_mass <= 0:
        return float(bands[0]["points"])

    expected = p_shutout * bands[0]["points"]
    scale_factor = (1.0 - p_shutout) / tail_mass

    lower = 0.5
    for band in bands[1:]:
        upper = band["max"] + 0.5
        prob = (cdf(upper) - cdf(lower)) * scale_factor
        expected += prob * band["points"]
        lower = upper

    threshold = bands[-1]["max"] + 0.5
    grid = np.linspace(threshold, max(160.0, mean_pa * 6), 2000)
    pdf = np.gradient(gammainc(shape, grid / scale), grid)
    charged = grid if pa.get("over_39_mode", "portion") == "total" else grid - bands[-1]["max"]
    expected += over_rate * float(np.trapezoid(pdf * charged, grid)) * scale_factor
    return expected


def score_kicker(
    *,
    games: float,
    xp_made_per_game: float,
    fg_attempts_per_game: float,
    distance_mix: dict[str, float],
    make_rates: dict[str, float],
    missed_fg_per_game: float = 0.0,
) -> ScoreBreakdown:
    k = config.scoring()["kicking"]
    comp = {"xp": xp_made_per_game * k["xp"] * games}

    values = {
        "under40": k["fg"],
        "fg40_49": k["fg"] + k["fg_40_49_bonus"],
        "fg50_plus": k["fg"] + k["fg_50_plus_bonus"],
    }
    for bucket, value in values.items():
        made = fg_attempts_per_game * distance_mix[bucket] * make_rates[bucket]
        comp[bucket] = made * value * games

    comp["missed_fg"] = missed_fg_per_game * k["missed_fg"] * games
    total = sum(comp.values())
    return ScoreBreakdown(total, total / max(games, 1.0), comp)


def score_defense(
    *,
    games: float,
    mean_points_allowed: float,
    sacks_per_game: float = 0.0,
    takeaways_per_game: float = 0.0,
    defensive_tds_per_season: float = 0.0,
    special_plays_per_season: float = 0.0,
    pa_volatility: float = 0.55,
) -> ScoreBreakdown:
    d = config.scoring()["dst"]
    comp = {
        "points_allowed": expected_points_allowed_points(mean_points_allowed, pa_volatility) * games,
        "sacks": sacks_per_game * d["sack"] * games,
        "takeaways": takeaways_per_game * d["interception"] * games,
        "defensive_td": defensive_tds_per_season * d["int_return_td"],
        "special": special_plays_per_season * d["xp_blocked"],
    }
    total = sum(comp.values())
    return ScoreBreakdown(total, total / max(games, 1.0), comp)
