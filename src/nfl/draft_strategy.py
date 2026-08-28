"""League-specific draft strategy notes for sheet tabs."""

from __future__ import annotations

from collections import Counter

from . import bye_weeks, config
from .value import Board, Valued, draftable, total_picks


def _ppr_label() -> str:
    reception = config.scoring()["receiving"]["reception"]
    if reception >= 1.0:
        return "full PPR"
    if reception >= 0.5:
        return "0.5 PPR"
    return "standard"


def _starter_summary() -> str:
    settings = config.settings()
    starters = settings["starters"]
    flex = settings.get("flex") or {}
    parts: list[str] = []
    for slot, count in starters.items():
        if slot in flex:
            eligible = "/".join(flex[slot])
            parts.append(f"{slot}×{count} ({eligible})")
        else:
            parts.append(f"{slot}×{count}")
    return ", ".join(parts)


def _round_band(entries: list[Valued], start: int, end: int) -> list[Valued]:
    return [entry for entry in entries if start <= entry.target_round <= end]


def _names(entries: list[Valued], limit: int = 5) -> str:
    if not entries:
        return "—"
    return ", ".join(entry.name for entry in entries[:limit])


def _position_round_targets(board: Board, position: str, rounds: tuple[int, int]) -> str:
    pool = [
        entry for entry in draftable(board)
        if entry.position == position and rounds[0] <= entry.target_round <= rounds[1]
    ]
    pool.sort(key=lambda entry: entry.value_rank)
    return _names(pool, 6)


def _value_cliff(board: Board, position: str) -> str:
    pool = board.by_position(position)
    if len(pool) < 8:
        return "thin pool"
    for index in range(4, min(len(pool) - 1, 24)):
        drop = pool[index - 1].value - pool[index].value
        if drop >= 12:
            return f"steep drop after ~{position}{index} ({pool[index - 1].name} → {pool[index].name})"
    return "gradual tier breaks"


def _bye_calendar_rows() -> list[list[str]]:
    rows: list[list[str]] = []
    for week in sorted(bye_weeks.HEAVY_BYE_WEEKS):
        teams_list = bye_weeks.teams_on_bye(week)
        flag = " ⚠ heavy" if len(teams_list) >= 6 else ""
        rows.append([f"Week {week}", ", ".join(teams_list) + f" ({len(teams_list)} teams){flag}"])
    return rows


def _bye_rules() -> list[list[str]]:
    return [
        [
            "Starter stacking",
            "Aim for no more than two starters (including FLEX) on the same bye week.",
        ],
        [
            "Heavy weeks",
            "Week 11 has six teams on bye (ATL, CLE, GB, LAR, NE, SEA). Spread risk there.",
        ],
        [
            "Handcuffs",
            "Backup RBs on your starters' bye weeks are fine — they fill the gap, not stack it.",
        ],
        [
            "Track on Draftable",
            "Use the bye column when marking Taken by = Me. Sort/filter before locking picks.",
        ],
    ]


def _espn_half_ppr_rounds(board: Board) -> list[list[str]]:
    top = draftable(board)
    return [
        [
            "Rounds 1–2",
            "Take the highest value on the board — usually RB/WR. "
            f"Typical targets: {_names(_round_band(top, 1, 2))}.",
        ],
        [
            "Rounds 3–5",
            "Finish RB2/WR2 and grab FLEX upside before the mid-tier cliff. "
            f"RB targets: {_position_round_targets(board, 'RB', (3, 5))}.",
        ],
        [
            "Rounds 6–8",
            "TE only if value clears the board (Warren/Kittle tier). Otherwise wait. "
            f"QB window opens around {_position_round_targets(board, 'QB', (6, 9))}.",
        ],
        [
            "Rounds 9–11",
            "Depth WR/RB with standalone value. Stream QB if you waited. "
            f"WR depth: {_position_round_targets(board, 'WR', (9, 11))}.",
        ],
        [
            "Rounds 12–13",
            "DST + K last two rounds unless a top-five unit falls. "
            "Do not reach — replacement is easy in-season.",
        ],
    ]


def _yahoo_full_ppr_rounds(board: Board) -> list[list[str]]:
    top = draftable(board)
    return [
        [
            "Rounds 1–3",
            "Full PPR + three WR starters pushes WR value early. "
            f"Elite tier: {_names(_round_band(top, 1, 3))}.",
        ],
        [
            "Rounds 4–6",
            "Secure WR3 and RB2 before the RB dead zone (~RB14). "
            f"{_value_cliff(board, 'RB')}.",
        ],
        [
            "Rounds 7–9",
            "TE premium if Kraft/Warren/LaPorta tier remains; else punt to round 10+. "
            f"QB value: {_position_round_targets(board, 'QB', (7, 10))}.",
        ],
        [
            "Rounds 10–12",
            "Best-ball WR/RB depth — receptions matter for flex-less rosters. "
            f"Targets: {_position_round_targets(board, 'WR', (10, 12))}.",
        ],
        [
            "Rounds 13–15",
            "DST and K in the final two rounds. Use earlier picks on skill depth, not bench TEs.",
        ],
    ]


def _core_philosophy(board: Board) -> list[list[str]]:
    settings = config.settings()
    flex_text = ", ".join(
        f"{pos} +{extra}" for pos, extra in board.flex_allocation.items() if extra
    ) or "none (no FLEX slot)"
    reception = config.scoring()["receiving"]["reception"]
    wr_note = (
        "Receptions are worth 1.0 — prioritize high-volume WRs in the first five rounds."
        if reception >= 1.0
        else "Half PPR — still lean RB early, but don't skip elite WR value."
    )
    return [
        ["Value method", "Draft by value (VOLS + BEER), not ADP. Positive edge_vs_board = market is slow."],
        ["Starters needed", str(board.starter_demand)],
        ["FLEX allocation", flex_text],
        ["Total picks", f"{settings['teams']} teams × {settings['draft_rounds']} rounds = {total_picks()}"],
        ["Scoring", _ppr_label()],
        ["Positional note", wr_note],
        ["RB depth", _value_cliff(board, "RB")],
        ["WR depth", _value_cliff(board, "WR")],
    ]


def build_rows(board: Board) -> list[list[str]]:
    settings = config.settings()
    profile = config.active_profile()
    rows: list[list[str]] = [
        ["DRAFT STRATEGY", settings.get("name", profile)],
        ["Profile", profile],
        ["League size", f"{settings['teams']} teams · {settings['draft_rounds']} rounds · snake"],
        ["Starters", _starter_summary()],
        ["", ""],
        ["CORE APPROACH", ""],
    ]
    rows.extend(_core_philosophy(board))
    rows.append(["", ""])
    rows.append(["ROUND-BY-ROUND PLAN", ""])
    if profile == "yahoo-full-ppr":
        rows.extend(_yahoo_full_ppr_rounds(board))
    else:
        rows.extend(_espn_half_ppr_rounds(board))

    rows.append(["", ""])
    rows.append(["BYE WEEK PLANNING", ""])
    rows.extend(_bye_rules())
    rows.append(["", ""])
    rows.append(["2026 BYE CALENDAR", "Teams off each week"])
    rows.extend(_bye_calendar_rows())

    # Summarize bye concentration among top draftable names
    bye_counts = Counter(
        bye_weeks.for_team(entry.team)
        for entry in draftable(board)[:40]
        if entry.position in {"QB", "RB", "WR", "TE"}
    )
    if bye_counts:
        rows.append(["", ""])
        rows.append(["TOP-40 BYE MIX", "Count of draftable skill players by bye week"])
        for week, count in sorted(bye_counts.items()):
            teams_list = ", ".join(bye_weeks.teams_on_bye(week))
            rows.append([f"Week {week}", f"{count} top names · teams: {teams_list}"])

    rows.append(["", ""])
    rows.append(
        [
            "Updated",
            "Regenerate with ./scripts/refresh_all.sh after roster or projection changes.",
        ]
    )
    return rows
