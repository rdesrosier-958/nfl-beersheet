"""Command line entry point: python -m nfl build"""

from __future__ import annotations

import argparse
import datetime as dt
import os

from . import adjustments, config, gsheet, output, projections, value


def _configure_league(profile: str | None) -> None:
    if profile:
        config.set_league(profile)
    elif os.environ.get("NFL_LEAGUE"):
        config.set_league(os.environ["NFL_LEAGUE"])


def cmd_build(args: argparse.Namespace) -> int:
    print(f"League profile: {config.active_profile()} ({config.settings().get('name', '')})")
    board_data = projections.build(offline=args.offline)

    log = adjustments.apply(board_data)
    if log:
        print("Applying news adjustments...")
        for line in log:
            print(line)

    board = value.build(board_data)
    written = output.write_all(board)

    print("\nWrote:")
    for path in written:
        print(f"  {path.relative_to(config.ROOT)}")

    if not args.no_sheet:
        _publish(board)

    if board.players:
        print("\nTop of the board:")
        for entry in board.players[:12]:
            delta = f"{entry.board_delta:+.0f}" if entry.board_delta is not None else "-"
            print(
                f"  {entry.value_rank:2d}. {entry.name:24s} {entry.position:4s}"
                f"{entry.team:4s} val {entry.value:+6.1f}  vs board {delta}"
            )
    else:
        print("\nNo players loaded — add manual CSVs under data/manual/ (see docs/updating.md)")

    print("\nLeague takeaways:")
    for line in output.takeaways(board):
        print(f"  - {line}")

    stamp = config.PROCESSED_DIR / "last_build.txt"
    stamp.write_text(dt.datetime.now().isoformat(timespec="seconds"))
    return 0


def _publish(board: value.Board) -> None:
    if not gsheet.configured():
        return
    try:
        url = gsheet.publish(board)
    except Exception as error:  # noqa: BLE001
        print(f"\n  ! Google Sheet not updated: {error}")
    else:
        print(f"  {url}")


def cmd_sheet(args: argparse.Namespace) -> int:
    board_data = projections.build(offline=True)
    adjustments.apply(board_data)
    board = value.build(board_data)
    print(gsheet.publish(board))
    return 0


def cmd_picks(args: argparse.Namespace) -> int:
    picks = value.snake_picks(args.slot)
    print(f"Draft slot {args.slot} of {config.settings()['teams']} picks at:")
    print("  " + ", ".join(f"R{i + 1}#{p}" for i, p in enumerate(picks)))
    return 0


def cmd_init_sheet(args: argparse.Namespace) -> int:
    """Create a new Google Sheet and save its id to config/sheet_id.txt.

    Requires the Google Drive API on the GCP project (in addition to Sheets).
    If that is not enabled, create a blank sheet in your Drive, share it with
    the service account email as Editor, and paste the URL into config/sheet_id.txt.
    """
    sheet_id = gsheet.create_sheet()
    print(f"Created sheet: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
    print(f"Saved id to {gsheet.SHEET_ID_FILE.relative_to(config.ROOT)}")
    print("\nShare this sheet with your Google account (Editor) so it shows in Drive.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nfl", description="NFL fantasy beer sheet builder")
    parser.add_argument(
        "--league",
        default=None,
        help="League profile name from config/leagues/ (default: espn-half-ppr)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="ingest sources, rescore, and write the sheet")
    build.add_argument("--offline", action="store_true", help="use cached projections")
    build.add_argument("--no-sheet", action="store_true", help="skip Google Sheets push")
    build.set_defaults(func=cmd_build)

    sheet = sub.add_parser("sheet", help="re-publish the cached board to Google Sheets")
    sheet.set_defaults(func=cmd_sheet)

    picks = sub.add_parser("picks", help="show snake pick numbers for a draft slot")
    picks.add_argument("slot", type=int)
    picks.set_defaults(func=cmd_picks)

    init_sheet = sub.add_parser("init-sheet", help="create a new Google Sheet and save its id")
    init_sheet.set_defaults(func=cmd_init_sheet)

    args = parser.parse_args(argv)
    _configure_league(args.league)
    return args.func(args)
