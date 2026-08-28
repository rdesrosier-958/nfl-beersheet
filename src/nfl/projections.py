"""Ingest live sources and manual CSVs, then build scored projections."""

from __future__ import annotations

import csv
import pickle
from pathlib import Path

from . import config, espn, fetch, parse, scoring
from .players import Player, Registry, normalise_position
from .records import Projection

STAT_COLUMNS = {
    "pass_yd", "pass_td", "pass_int",
    "rush_yd", "rush_td",
    "rec", "rec_yd", "rec_td", "return_td",
}
OFFENSE = {"QB", "RB", "WR", "TE"}
CACHE = config.projections_cache()


def _float(value: str | None, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return default


def _int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open() as handle:
        lines = [line for line in handle if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def _norm_header(row: dict[str, str | None]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in row.items():
        if not key:
            continue
        out[key.strip().lower().replace(" ", "_")] = (value or "").strip()
    return out


def ingest_espn(registry: Registry, source_id: str) -> int:
    season = int(config.settings().get("season", 2026))
    players = espn.fetch_projections(season=season)
    for row in players:
        player = registry.add(
            name=row.name, team_raw=row.team, position=row.position,
            source_id=source_id, rank=row.rank,
        )
        if player is None:
            continue
        player.stats = dict(row.stats)
        player.stat_source = source_id
        player.espn_points = row.espn_points
    return len(players)


def ingest_rotoballer(registry: Registry, source_id: str, *, offline: bool = False) -> int:
    source = next(s for s in config.sources()["sources"] if s["id"] == source_id)
    fetched = fetch.fetch(source_id, source["url"], offline=offline)
    if fetched is None:
        return 0
    rows = parse.parse_rotoballer_rankings(fetched.html)
    for row in rows:
        registry.add(
            name=row.player, team_raw=row.team_raw, position=row.position,
            source_id=source_id, rank=row.source_rank,
        )
    return len(rows)


def ingest_yahoo(registry: Registry, source_id: str, *, offline: bool = False) -> int:
    pdf_path = config.MANUAL_DIR / "yahoo_top300.pdf"
    if pdf_path.exists():
        rows = parse.parse_yahoo_pdf(pdf_path)
        for row in rows:
            registry.add_yahoo_rank(
                short_name=row.player, team_raw=row.team_raw, position=row.position,
                source_id=source_id, rank=row.source_rank,
            )
        return len(rows)

    source = next(s for s in config.sources()["sources"] if s["id"] == source_id)
    fetched = fetch.fetch(source_id, source["url"], offline=offline)
    rows: list[parse.RankingRow] = []
    if fetched is not None:
        rows = parse.parse_yahoo_rankings(fetched.html)

    if not rows:
        path = config.MANUAL_DIR / "yahoo_rankings.csv"
        if path.exists():
            return _ingest_yahoo_csv(registry, source_id, path)
        print(f"  ! {source_id}: save PDF to {pdf_path.name} or CSV to yahoo_rankings.csv")
        return 0

    for row in rows:
        registry.add_yahoo_rank(
            short_name=row.player, team_raw=row.team_raw, position=row.position,
            source_id=source_id, rank=row.source_rank,
        )
    return len(rows)


def _ingest_yahoo_csv(registry: Registry, source_id: str, path: Path) -> int:
    count = 0
    for raw in _read_csv(path):
        row = _norm_header(raw)
        name = row.get("player") or row.get("name")
        if not name:
            continue
        rank = _int(row.get("rank")) or count + 1
        registry.add(
            name=name,
            team_raw=row.get("team") or row.get("yahoo_team") or "",
            position=row.get("position") or row.get("pos") or "",
            source_id=source_id,
            rank=rank,
        )
        count += 1
    return count


def ingest_subvertadown_csv(path: Path, registry: Registry) -> int:
    rows = _read_csv(path)
    count = 0
    for raw in rows:
        row = _norm_header(raw)
        name = row.get("player") or row.get("name")
        if not name:
            continue
        position = row.get("position") or row.get("pos") or ""
        resolved = normalise_position(position, name)
        if resolved is None:
            continue
        team = row.get("team") or ""
        val = _float(row.get("val") or row.get("value"), default=0.0) or None
        adp = _float(row.get("adp") or row.get("round_adp"), default=0.0) or None
        bye = _int(row.get("bye"))
        player = registry.find(name, resolved) or registry.add(
            name=name, team_raw=team, position=resolved,
            source_id="subvertadown", rank=count + 1,
        )
        if player is None:
            continue
        if val is not None:
            player.subvertadown_val = val
        if adp is not None:
            player.subvertadown_adp = adp
        if bye is not None:
            player.bye = bye
        count += 1
    return count


def _average_ranks(ranks: dict[str, int]) -> float | None:
    if not ranks:
        return None
    return sum(ranks.values()) / len(ranks)


def _index_positional_ranks(registry: Registry) -> None:
    by_position: dict[str, list[Player]] = {}
    for player in registry.all():
        by_position.setdefault(player.position, []).append(player)

    for pool in by_position.values():
        for source_id in {sid for p in pool for sid in p.source_ranks}:
            ranked = sorted(
                [p for p in pool if source_id in p.source_ranks],
                key=lambda p: p.source_ranks[source_id],
            )
            for index, player in enumerate(ranked, start=1):
                player.source_pos_ranks.setdefault(source_id, index)


def _score_player(player: Player, games: float) -> Projection:
    position = player.position
    if position in OFFENSE:
        stats = dict(player.stats)
        score = scoring.score_offense(stats, games, volatility=scoring.volatility_for(position))
        return Projection(
            player=player,
            position=position,
            team=player.team,
            games=games,
            stats=stats,
            points=score.total,
            per_game=score.per_game,
            components=score.components,
            projection_basis=player.stat_source or "rank-only",
            market_rank=_average_ranks(player.source_overall_ranks),
            market_pos_rank=_average_ranks(player.source_pos_ranks),
            market_sources=len(player.source_pos_ranks) or len(player.source_ranks),
            subvertadown_val=player.subvertadown_val,
            subvertadown_adp=player.subvertadown_adp,
            bye=player.bye,
        )

    if player.espn_points and player.espn_points > 0:
        per_game = player.espn_points / max(games, 1.0)
        return Projection(
            player=player, position=position, team=player.team, games=games,
            stats=dict(player.stats), points=player.espn_points, per_game=per_game,
            components={"espn_projection": player.espn_points},
            projection_basis=player.stat_source or "espn",
            market_rank=_average_ranks(player.source_overall_ranks),
            market_pos_rank=_average_ranks(player.source_pos_ranks),
            market_sources=len(player.source_pos_ranks),
            subvertadown_val=player.subvertadown_val,
            subvertadown_adp=player.subvertadown_adp,
            bye=player.bye,
        )

    if position == "K":
        score = scoring.score_kicker(
            games=games,
            xp_made_per_game=player.stats.get("xp_pg", 2.0),
            fg_attempts_per_game=player.stats.get("fg_att_pg", 1.8),
            distance_mix={
                "under40": player.stats.get("fg_u40_mix", 0.55),
                "fg40_49": player.stats.get("fg_40_mix", 0.30),
                "fg50_plus": player.stats.get("fg_50_mix", 0.15),
            },
            make_rates={"under40": 0.95, "fg40_49": 0.88, "fg50_plus": 0.65},
        )
        return Projection(
            player=player, position=position, team=player.team, games=games,
            stats=dict(player.stats), points=score.total, per_game=score.per_game,
            components=score.components, projection_basis=player.stat_source or "model",
            market_rank=_average_ranks(player.source_overall_ranks),
            market_pos_rank=_average_ranks(player.source_pos_ranks),
            market_sources=len(player.source_pos_ranks),
            subvertadown_val=player.subvertadown_val,
            subvertadown_adp=player.subvertadown_adp,
            bye=player.bye,
        )

    score = scoring.score_defense(
        games=games,
        mean_points_allowed=player.stats.get("pa_pg", 22.0),
        sacks_per_game=player.stats.get("sack_pg", 2.5),
        takeaways_per_game=player.stats.get("to_pg", 1.2),
        defensive_tds_per_season=player.stats.get("def_td", 2.0),
    )
    return Projection(
        player=player, position=position, team=player.team, games=games,
        stats=dict(player.stats), points=score.total, per_game=score.per_game,
        components=score.components, projection_basis=player.stat_source or "model",
        market_rank=_average_ranks(player.source_overall_ranks),
        market_pos_rank=_average_ranks(player.source_pos_ranks),
        market_sources=len(player.source_pos_ranks),
        subvertadown_val=player.subvertadown_val,
        subvertadown_adp=player.subvertadown_adp,
        bye=player.bye,
    )


def build(*, offline: bool = False) -> list[Projection]:
    if offline and CACHE.exists():
        return pickle.loads(CACHE.read_bytes())

    registry = Registry()
    loaded: list[str] = []
    season = int(config.settings().get("season", 2026))
    default_games = float(config.settings().get("games", 17))

    for source in config.sources()["sources"]:
        kind = source["kind"]
        source_id = source["id"]
        if kind == "espn_projections":
            n = ingest_espn(registry, source_id)
            print(f"  {source_id}: {n} projections")
        elif kind == "rotoballer_ranking":
            n = ingest_rotoballer(registry, source_id, offline=offline)
            print(f"  {source_id}: {n} ranked")
        elif kind == "yahoo_ranking":
            n = ingest_yahoo(registry, source_id, offline=offline)
            if n:
                print(f"  {source_id}: {n} ranked")
        elif kind == "subvertadown_csv":
            path = config.ROOT / source["path"]
            n = ingest_subvertadown_csv(path, registry)
            if n:
                print(f"  {source_id}: {n} reference rows")
        if kind != "yahoo_ranking" and kind != "subvertadown_csv":
            if kind == "espn_projections" or kind == "rotoballer_ranking":
                loaded.append(f"{source_id}")

    _index_positional_ranks(registry)
    projections: list[Projection] = []
    for player in registry.all():
        if not player.stats and not player.espn_points:
            continue
        games = default_games
        scored = _score_player(player, games)
        if scored.points > 0:
            projections.append(scored)

    projections.sort(key=lambda p: -p.points)
    loaded_summary = config.PROCESSED_DIR / "sources_loaded.txt"
    CACHE.write_bytes(pickle.dumps(projections))
    loaded_summary.write_text(
        f"players={len(projections)} season={season}\n" + "\n".join(loaded)
    )
    return projections
