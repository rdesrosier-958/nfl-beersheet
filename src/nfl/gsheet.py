"""Publish the board to a Google Sheet.

Create a blank sheet in your Drive, share it with the service account as Editor,
and save the id to config/sheet_id.txt. The Draftable tab keeps a Taken-by
dropdown (Me / Other) that survives refreshes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import gspread
import pandas as pd

from . import config, output
from .value import Board, draftable

CREDENTIALS_ENV = "NFL_GOOGLE_CREDENTIALS"
CREDENTIALS_JSON_ENV = "NFL_GOOGLE_CREDENTIALS_JSON"
# Same service account as cff-beersheet; cloud automations may only have this set.
SHARED_CREDENTIALS_ENV = "CFF_GOOGLE_CREDENTIALS"
SHARED_CREDENTIALS_JSON_ENV = "CFF_GOOGLE_CREDENTIALS_JSON"
SHEET_ENV = "NFL_SHEET_ID"
DEFAULT_CREDENTIALS = config.CONFIG_DIR / "service-account.json"
SHEET_ID_FILE = config.CONFIG_DIR / "sheet_id.txt"

OWNER = "Taken by"
OWNER_ME = "Me"
OWNER_OTHER = "Other"
OWNER_CHOICES = (OWNER_ME, OWNER_OTHER)

GREY = {"red": 0.94, "green": 0.94, "blue": 0.94}
HEADER_BG = {"red": 0.12, "green": 0.12, "blue": 0.12}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
ME_BG = {"red": 0.75, "green": 0.90, "blue": 0.78}
OTHER_BG = {"red": 0.88, "green": 0.88, "blue": 0.88}
OTHER_FG = {"red": 0.55, "green": 0.55, "blue": 0.55}


class NotConfigured(RuntimeError):
    """Raised when credentials or the sheet id are missing."""


def credentials_path() -> Path:
    raw = os.environ.get(CREDENTIALS_ENV) or os.environ.get(SHARED_CREDENTIALS_ENV)
    path = Path(raw).expanduser() if raw else DEFAULT_CREDENTIALS
    if not path.exists():
        raise NotConfigured(
            f"No service account key at {path}. Copy from cff-beersheet or set "
            f"{CREDENTIALS_ENV}, {SHARED_CREDENTIALS_ENV}, {CREDENTIALS_JSON_ENV}, or "
            f"{SHARED_CREDENTIALS_JSON_ENV}. See README."
        )
    return path


def _credentials_json() -> str | None:
    return os.environ.get(CREDENTIALS_JSON_ENV) or os.environ.get(
        SHARED_CREDENTIALS_JSON_ENV
    )


def _client() -> gspread.Client:
    inline = _credentials_json()
    if inline:
        try:
            return gspread.service_account_from_dict(json.loads(inline))
        except json.JSONDecodeError as error:
            raise NotConfigured(
                f"{CREDENTIALS_JSON_ENV} / {SHARED_CREDENTIALS_JSON_ENV} is not valid JSON: {error}"
            ) from error
    return gspread.service_account(filename=str(credentials_path()))


def sheet_id() -> str:
    raw = os.environ.get(SHEET_ENV)
    if not raw and SHEET_ID_FILE.exists():
        raw = SHEET_ID_FILE.read_text().strip()
    if not raw:
        raise NotConfigured(
            f"No sheet id. Write it to {SHEET_ID_FILE} or set {SHEET_ENV}."
        )
    return extract_id(raw)


def extract_id(raw: str) -> str:
    raw = raw.strip()
    if "/d/" in raw:
        return raw.split("/d/", 1)[1].split("/", 1)[0]
    return raw


def configured() -> bool:
    try:
        if not _credentials_json():
            credentials_path()
        sheet_id()
    except NotConfigured:
        return False
    return True


def _frames(board: Board) -> list[tuple[str, pd.DataFrame]]:
    full = pd.DataFrame([output._row(entry) for entry in board.players])
    top = pd.DataFrame([output._row(entry) for entry in draftable(board)])

    tabs: list[tuple[str, pd.DataFrame]] = [
        ("Draftable", top),
        ("Big Board", full),
    ]
    for position in ("QB", "RB", "WR", "TE", "K", "DST"):
        subset = full[full["pos"] == position]
        if not subset.empty:
            tabs.append((position, subset.reset_index(drop=True)))
    return tabs


def _values(frame: pd.DataFrame) -> list[list]:
    header = [str(column) for column in frame.columns]
    body = frame.astype(object).where(frame.notna(), "").values.tolist()
    return [header] + [[_cell(v) for v in row] for row in body]


def _cell(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def publish(board: Board) -> str:
    book = _client().open_by_key(sheet_id())
    owners = read_owners(book)
    tabs = _frames(board)
    existing = {sheet.title: sheet for sheet in book.worksheets()}
    requests: list[dict] = []

    for title, frame in tabs:
        rows, columns = len(frame) + 1, len(frame.columns)
        drafted_tab = title == "Draftable"
        if drafted_tab:
            columns += 1

        sheet = existing.get(title)
        if sheet is None:
            sheet = book.add_worksheet(title=title, rows=max(rows, 2), cols=max(columns, 2))
            existing[title] = sheet
        else:
            sheet.clear()
        if sheet.row_count < rows or sheet.col_count < columns:
            sheet.resize(rows=max(rows, sheet.row_count), cols=max(columns, sheet.col_count))

        values = _values(frame)
        if drafted_tab:
            names = [""] + [str(row[0]) for row in frame[["player"]].values]
            values = [
                [owners.get(names[index], "") if index else OWNER] + row
                for index, row in enumerate(values)
            ]
        sheet.update(values=values, range_name="A1", value_input_option="USER_ENTERED")
        requests += _format(sheet.id, frame, drafted_tab=drafted_tab)

    for title, sheet in existing.items():
        if title not in {name for name, _ in tabs}:
            requests.append({"deleteSheet": {"sheetId": sheet.id}})

    requests += _reorder([existing[name].id for name, _ in tabs])
    book.batch_update({"requests": requests})
    return f"https://docs.google.com/spreadsheets/d/{book.id}/edit"


def read_owners(book=None) -> dict[str, str]:
    if book is None:
        if not configured():
            return {}
        book = _client().open_by_key(sheet_id())
    try:
        sheet = book.worksheet("Draftable")
    except gspread.WorksheetNotFound:
        return {}
    rows = sheet.get_all_values()
    if not rows or rows[0][0] != OWNER:
        return {}

    try:
        name_column = rows[0].index("player")
    except ValueError:
        return {}

    owners: dict[str, str] = {}
    for row in rows[1:]:
        if len(row) <= name_column:
            continue
        name = row[name_column].strip()
        raw = row[0].strip()
        if name and raw in OWNER_CHOICES:
            owners[name] = raw
    return owners


def create_sheet(title: str | None = None) -> str:
    """Create a new spreadsheet owned by the service account; returns its id."""
    league = config.settings().get("name", "NFL Beer Sheet")
    book = _client().create(title or f"{league} — Beer Sheet")
    SHEET_ID_FILE.write_text(book.id)
    return book.id


def _format(sheet_id_: int, frame: pd.DataFrame, *, drafted_tab: bool) -> list[dict]:
    columns = list(frame.columns)
    offset = 1 if drafted_tab else 0
    width = len(columns) + offset
    rows = len(frame) + 1

    def span(start: int, end: int, first_row: int = 0) -> dict:
        return {
            "sheetId": sheet_id_, "startRowIndex": first_row, "endRowIndex": rows,
            "startColumnIndex": start, "endColumnIndex": end,
        }

    requests: list[dict] = [
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id_, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": span(0, width, first_row=0) | {"endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEADER_BG,
                "textFormat": {"bold": True, "foregroundColor": WHITE, "fontSize": 10},
                "verticalAlignment": "MIDDLE",
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
        }},
        {"setBasicFilter": {"filter": {"range": span(0, width)}}},
    ]

    decimals = {
        "proj_points": "0.0", "ppg": "0.00", "value": "0.0", "vols": "0.0", "beer": "0.0",
        "subvertadown_val": "0.0", "subvertadown_adp": "0.0",
    }
    for name, pattern in decimals.items():
        if name in columns:
            index = columns.index(name) + offset
            requests.append({"repeatCell": {
                "range": span(index, index + 1, first_row=1),
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": pattern}}},
                "fields": "userEnteredFormat.numberFormat",
            }})

    if "edge_vs_board" in columns:
        index = columns.index("edge_vs_board") + offset
        requests.append({"repeatCell": {
            "range": span(index, index + 1, first_row=1),
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "+0;-0;0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }})

    if "value" in columns:
        index = columns.index("value") + offset
        requests.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [span(index, index + 1, first_row=1)],
            "gradientRule": {
                "minpoint": {"color": {"red": 0.96, "green": 0.80, "blue": 0.80}, "type": "MIN"},
                "midpoint": {"color": WHITE, "type": "NUMBER", "value": "0"},
                "maxpoint": {"color": {"red": 0.74, "green": 0.89, "blue": 0.78}, "type": "MAX"},
            },
        }}})

    if "tier" in columns:
        index = columns.index("tier") + offset
        letter = _letter(index)
        requests.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [span(0, width, first_row=1)],
            "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [
                    {"userEnteredValue": f"=ISEVEN(${letter}2)"}
                ]},
                "format": {"backgroundColor": GREY},
            },
        }}})

    if drafted_tab:
        owner_range = {
            "sheetId": sheet_id_, "startRowIndex": 1, "endRowIndex": rows,
            "startColumnIndex": 0, "endColumnIndex": 1,
        }
        requests += [
            {"setDataValidation": {"range": owner_range, "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": choice} for choice in OWNER_CHOICES],
                },
                "showCustomUi": True, "strict": False,
            }}},
            {"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [span(0, width, first_row=1)],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA", "values": [
                        {"userEnteredValue": f'=$A2="{OWNER_ME}"'}
                    ]},
                    "format": {"backgroundColor": ME_BG},
                },
            }}},
            {"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [span(0, width, first_row=1)],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA", "values": [
                        {"userEnteredValue": f'=$A2="{OWNER_OTHER}"'}
                    ]},
                    "format": {
                        "backgroundColor": OTHER_BG,
                        "textFormat": {"strikethrough": True, "foregroundColor": OTHER_FG},
                    },
                },
            }}},
        ]

    requests += _widths(sheet_id_, frame, offset)
    return requests


def _widths(sheet_id_: int, frame: pd.DataFrame, offset: int) -> list[dict]:
    requests = []
    if offset:
        requests.append(_width(sheet_id_, 0, 80))
    for index, column in enumerate(frame.columns):
        longest = max(
            [len(str(column))] + [len(str(v)) for v in frame[column].head(200)],
            default=8,
        )
        pixels = min(max(longest * 7 + 16, 52), 420)
        requests.append(_width(sheet_id_, index + offset, pixels))
    return requests


def _width(sheet_id_: int, index: int, pixels: int) -> dict:
    return {"updateDimensionProperties": {
        "range": {"sheetId": sheet_id_, "dimension": "COLUMNS",
                  "startIndex": index, "endIndex": index + 1},
        "properties": {"pixelSize": pixels},
        "fields": "pixelSize",
    }}


def _reorder(sheet_ids: list[int]) -> list[dict]:
    return [
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id_, "index": position},
            "fields": "index",
        }}
        for position, sheet_id_ in enumerate(sheet_ids)
    ]


def _letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
