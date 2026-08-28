"""ESPN fantasy projections via the public lm-api-reads endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from . import teams

API_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leaguedefaults/3"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DST"}
PRO_TEAMS = {
    1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN", 8: "DET",
    9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA", 16: "MIN",
    17: "NE", 18: "NO", 19: "NYG", 20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC",
    25: "SF", 26: "SEA", 27: "TB", 28: "WAS", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}

# ESPN stat id -> internal season-total key
STAT_MAP = {
    "3": "pass_yd",
    "4": "pass_td",
    "20": "pass_int",
    "24": "rush_yd",
    "25": "rush_td",
    "53": "rec",
    "42": "rec_yd",
    "43": "rec_td",
    "101": "return_td_kr",
    "102": "return_td_pr",
}


@dataclass
class EspnPlayer:
    name: str
    position: str
    team: str
    rank: int
    games: float
    stats: dict[str, float]
    espn_points: float


def _season_projection(stat_rows: list[dict], season: int) -> dict | None:
    for row in stat_rows:
        if row.get("statSourceId") == 1 and row.get("scoringPeriodId") == 0 and row.get("seasonId") == season:
            return row
    for row in stat_rows:
        if row.get("statSourceId") == 1 and row.get("scoringPeriodId") == 0:
            return row
    return None


def _extract_stats(raw: dict[str, float]) -> dict[str, float]:
    stats: dict[str, float] = {}
    for espn_id, key in STAT_MAP.items():
        value = raw.get(espn_id)
        if value is not None:
            stats[key] = float(value)
    if stats.get("return_td_kr") or stats.get("return_td_pr"):
        stats["return_td"] = stats.get("return_td_kr", 0.0) + stats.get("return_td_pr", 0.0)
        stats.pop("return_td_kr", None)
        stats.pop("return_td_pr", None)
    return stats


def _parse_entry(entry: dict, season: int) -> EspnPlayer | None:
    player = entry.get("player") or {}
    position = POSITIONS.get(player.get("defaultPositionId"))
    if position is None:
        return None

    name = player.get("fullName") or ""
    if not name:
        return None

    team = PRO_TEAMS.get(player.get("proTeamId"), "")
    if position == "DST" and not team and " " in name:
        # "Texans D/ST" -> HOU via nickname is unreliable; prefer proTeamId.
        pass
    team = teams.canonical(team) or team

    ranks = (player.get("draftRanksByRankType") or {}).get("PPR") or {}
    rank = int(ranks.get("rank") or 9999)

    projection = _season_projection(player.get("stats") or [], season)
    if projection is None:
        return None

    raw_stats = projection.get("stats") or {}
    stats = _extract_stats({str(k): float(v) for k, v in raw_stats.items()})
    games = float(raw_stats.get("210") or raw_stats.get(210) or 17)
    espn_points = float(projection.get("appliedTotal") or 0.0)

    return EspnPlayer(name, position, team, rank, games, stats, espn_points)


def fetch_projections(*, season: int | None = None, limit: int = 600) -> list[EspnPlayer]:
    season = season or 2026
    url = API_BASE.format(season=season)
    players: list[EspnPlayer] = []
    seen: set[tuple[str, str]] = set()

    for offset in range(0, limit, 50):
        fantasy_filter = {
            "players": {
                "limit": 50,
                "offset": offset,
                "sortDraftRanks": {"sortPriority": 100, "sortAsc": True, "value": "PPR"},
                "filterStatsForSourceIds": {"value": [1]},
            }
        }
        response = requests.get(
            url,
            headers={**HEADERS, "X-Fantasy-Filter": json.dumps(fantasy_filter)},
            params={"view": "kona_playercard", "scoringPeriodId": 0},
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json().get("players") or []
        if not batch:
            break
        for entry in batch:
            parsed = _parse_entry(entry, season)
            if parsed is None:
                continue
            key = (parsed.name, parsed.position)
            if key in seen:
                continue
            seen.add(key)
            players.append(parsed)

    players.sort(key=lambda p: p.rank)
    return players
