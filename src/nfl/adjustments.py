"""Manual news adjustments."""

from __future__ import annotations

import csv
import datetime as dt

from . import config, scoring
from .records import Projection

PATH = config.MANUAL_DIR / "adjustments.csv"
OFFENSE = {"QB", "RB", "WR", "TE"}


def load() -> list[dict]:
    if not PATH.exists():
        return []
    with PATH.open() as handle:
        lines = [line for line in handle if not line.lstrip().startswith("#")]
    rows = [row for row in csv.DictReader(lines) if row.get("player")]
    today = dt.date.today()
    live: list[dict] = []
    for row in rows:
        expires = (row.get("expires") or "").strip()
        if expires:
            try:
                if dt.date.fromisoformat(expires) < today:
                    continue
            except ValueError:
                pass
        live.append(row)
    return live


def apply(projections: list[Projection]) -> list[str]:
    rows = load()
    if not rows:
        return []

    index: dict[tuple[str, str], Projection] = {}
    for projection in projections:
        index[(projection.player.key, projection.position)] = projection

    from .players import name_key

    log: list[str] = []
    for row in rows:
        key = (name_key(row["player"]), (row.get("position") or "").upper())
        target = index.get(key)
        if target is None:
            log.append(f"  ! no match for {row['player']} ({row.get('position')})")
            continue

        status = (row.get("status") or "").strip().upper()
        if status in {"OUT", "SEASON", "IR"}:
            factor = 0.0
        else:
            try:
                factor = 1.0 + float(row.get("adjust_pct") or 0) / 100.0
            except ValueError:
                factor = 1.0
        factor = max(factor, 0.0)

        if target.position in OFFENSE:
            target.stats = {stat: value * factor for stat, value in target.stats.items()}
            score = scoring.score_offense(
                target.stats, target.games,
                volatility=scoring.volatility_for(target.position),
            )
            target.points, target.per_game = score.total, score.per_game
            target.components = score.components
        else:
            target.points *= factor
            target.per_game *= factor

        note = (row.get("note") or "").strip()
        target.notes = f"{target.notes} | {note}".strip(" |") if target.notes else note
        log.append(f"  adjusted {target.name} ({target.position}) x{factor:.2f} - {note}")

    return log
