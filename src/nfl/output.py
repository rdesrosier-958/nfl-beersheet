"""Write beer sheet CSV and Excel output."""

from __future__ import annotations

import csv
import datetime as dt

import pandas as pd

from . import config, draft_strategy
from .value import Board, Valued, draftable, snake_picks

COLUMNS = [
    "rank", "round", "player", "pos", "pos_rank", "team", "tier",
    "proj_points", "ppg", "value", "vols", "beer",
    "board_pos_rank", "edge_vs_board", "board_overall_rank",
    "subvertadown_val", "subvertadown_adp",
    "bye", "basis", "notes",
]


def _row(entry: Valued) -> dict:
    projection = entry.projection
    return {
        "rank": entry.value_rank,
        "round": entry.target_round,
        "player": entry.name,
        "pos": entry.position,
        "pos_rank": f"{entry.position}{entry.position_rank}",
        "team": entry.team,
        "tier": entry.tier,
        "proj_points": round(projection.points, 1),
        "ppg": round(projection.per_game, 2),
        "value": round(entry.value, 1),
        "vols": round(entry.vols, 1),
        "beer": round(entry.beer, 1),
        "board_pos_rank": (
            f"{entry.position}{entry.board_pos_rank:.0f}"
            if entry.board_pos_rank is not None else ""
        ),
        "edge_vs_board": round(entry.board_delta, 1) if entry.board_delta is not None else "",
        "board_overall_rank": round(entry.board_rank, 1) if entry.board_rank is not None else "",
        "subvertadown_val": (
            round(projection.subvertadown_val, 1)
            if projection.subvertadown_val is not None else ""
        ),
        "subvertadown_adp": (
            round(projection.subvertadown_adp, 1)
            if projection.subvertadown_adp is not None else ""
        ),
        "bye": projection.bye or "",
        "basis": projection.projection_basis,
        "notes": projection.notes,
    }


def write_csv(board: Board) -> list:
    written = []
    full = config.output_dir() / "beersheet.csv"
    with full.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for entry in board.players:
            writer.writerow(_row(entry))
    written.append(full)

    top = config.output_dir() / "beersheet_draftable.csv"
    with top.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for entry in draftable(board):
            writer.writerow(_row(entry))
    written.append(top)
    return written


def write_excel(board: Board) -> list:
    path = config.output_dir() / "beersheet.xlsx"
    frame = pd.DataFrame([_row(entry) for entry in board.players])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        strategy = pd.DataFrame(
            draft_strategy.build_rows(board),
            columns=["section", "detail"],
        )
        strategy.to_excel(writer, sheet_name="Draft Strategy", index=False, header=False)
        frame.to_excel(writer, sheet_name="Big Board", index=False)
        top = pd.DataFrame([_row(entry) for entry in draftable(board)])
        top.to_excel(writer, sheet_name="Draftable", index=False)
        for position in ("QB", "RB", "WR", "TE", "K", "DST"):
            subset = frame[frame["pos"] == position]
            if not subset.empty:
                subset.to_excel(writer, sheet_name=position, index=False)

    return [path]


def takeaways(board: Board) -> list[str]:
    settings = config.settings()
    teams = settings["teams"]
    picks = settings["teams"] * settings["draft_rounds"]
    flex = board.flex_allocation
    flex_text = ", ".join(f"{pos} +{extra}" for pos, extra in flex.items() if extra)
    lines = [
        f"{teams}-team league, {picks} total picks, snake draft",
        f"Starters demand roughly {board.starter_demand}",
        f"Flex allocation (greedy): {flex_text or 'none'}",
        f"Top QB value: {board.by_position('QB')[0].name if board.by_position('QB') else 'n/a'}",
    ]
    return lines


def write_all(board: Board) -> list:
    written = write_csv(board) + write_excel(board)
    meta = config.output_dir() / "build_meta.txt"
    meta.write_text(dt.datetime.now().isoformat(timespec="seconds"))
    written.append(meta)
    return written


def pick_chart(slot: int) -> str:
    picks = snake_picks(slot)
    return ", ".join(f"R{i + 1}#{p}" for i, p in enumerate(picks))
