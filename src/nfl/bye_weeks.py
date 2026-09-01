"""2026 NFL regular-season bye weeks by team abbreviation."""

from __future__ import annotations

from . import teams

# Official 2026 schedule: byes in weeks 5–14, none in week 12.
BYE_WEEK_2026: dict[str, int] = {
    "ARI": 14,
    "ATL": 11,
    "BAL": 13,
    "BUF": 7,
    "CAR": 5,
    "CHI": 10,
    "CIN": 6,
    "CLE": 11,
    "DAL": 14,
    "DEN": 10,
    "DET": 6,
    "GB": 11,
    "HOU": 8,
    "IND": 13,
    "JAX": 7,
    "KC": 5,
    "LV": 13,
    "LAC": 7,
    "LAR": 11,
    "MIA": 6,
    "MIN": 6,
    "NE": 11,
    "NO": 8,
    "NYG": 8,
    "NYJ": 13,
    "PHI": 10,
    "PIT": 9,
    "SF": 8,
    "SEA": 11,
    "TB": 10,
    "TEN": 9,
    "WAS": 7,
}

HEAVY_BYE_WEEKS: dict[int, tuple[str, ...]] = {
    week: tuple(sorted(team for team, bye in BYE_WEEK_2026.items() if bye == week))
    for week in sorted({week for week in BYE_WEEK_2026.values()})
}


def for_team(team: str | None) -> int | None:
    code = teams.canonical(team or "")
    if not code:
        return None
    return BYE_WEEK_2026.get(code)


def teams_on_bye(week: int) -> tuple[str, ...]:
    return HEAVY_BYE_WEEKS.get(week, ())
