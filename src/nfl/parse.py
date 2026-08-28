"""Turn fetched HTML/PDF into ranking rows."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from . import teams

_YAHOO_LINE = re.compile(r"^(\d+)\s+(.+)$")
_YAHOO_POS = re.compile(r"•(QB|RB|WR|TE|K|D/ST|DST)\b")


@dataclass
class RankingRow:
    source_rank: int
    player: str
    team_raw: str
    position: str


def _num(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("+", "").strip()
    if not cleaned or cleaned in {"-", "--", "N/A"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_rotoballer_rankings(html: str) -> list[RankingRow]:
    """Parse Rotoballer top-400 table: Tier, Rank, Player Name, Pos."""
    soup = BeautifulSoup(html, "lxml")
    best: list[RankingRow] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 50:
            continue
        headers = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        rank_idx = next((i for i, h in enumerate(headers) if h.startswith("rank")), None)
        name_idx = next((i for i, h in enumerate(headers) if "player" in h or h == "name"), None)
        pos_idx = next((i for i, h in enumerate(headers) if h in {"pos", "position"}), None)
        if rank_idx is None or name_idx is None:
            continue

        parsed: list[RankingRow] = []
        for row in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) <= max(rank_idx, name_idx):
                continue
            rank = _num(cells[rank_idx])
            if rank is None:
                continue
            name = cells[name_idx]
            position = cells[pos_idx].upper() if pos_idx is not None and pos_idx < len(cells) else ""
            if position in {"D/ST", "DEF"}:
                position = "DST"
            parsed.append(RankingRow(int(rank), name, "", position))

        if len(parsed) > len(best):
            best = parsed

    return best


def parse_yahoo_rankings(html: str) -> list[RankingRow]:
    """Parse Yahoo consensus rankings when the article body is server-rendered."""
    soup = BeautifulSoup(html, "lxml")
    rows: list[RankingRow] = []

    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if len(trs) < 20:
            continue
        headers = [c.get_text(strip=True).lower() for c in trs[0].find_all(["th", "td"])]
        if not any("rank" in h for h in headers):
            continue
        name_idx = next((i for i, h in enumerate(headers) if "player" in h or h == "name"), None)
        pos_idx = next((i for i, h in enumerate(headers) if h in {"pos", "position"}), None)
        team_idx = next((i for i, h in enumerate(headers) if h == "team"), None)
        if name_idx is None:
            continue

        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) <= name_idx:
                continue
            rank = _num(cells[0])
            if rank is None:
                continue
            name = cells[name_idx]
            team = cells[team_idx] if team_idx is not None and team_idx < len(cells) else ""
            position = cells[pos_idx].upper() if pos_idx is not None and pos_idx < len(cells) else ""
            if position in {"D/ST", "DEF"}:
                position = "DST"
            rows.append(RankingRow(int(rank), name, team, position))

    return rows


def _split_yahoo_name_team(text: str) -> tuple[str, str]:
    """Split 'J. GibbsDET' or 'J. Smith-NjigbaSEA' into name and team."""
    cleaned = unicodedata.normalize("NFKC", text).strip()
    for code in sorted(teams.CODES, key=len, reverse=True):
        if cleaned.endswith(code) and len(cleaned) > len(code):
            return cleaned[: -len(code)].strip(), code
    return cleaned, ""


def _parse_yahoo_pdf_line(line: str) -> RankingRow | None:
    match = _YAHOO_LINE.match(line.strip())
    if not match:
        return None
    rank = int(match.group(1))
    if rank > 300:
        return None
    rest = match.group(2)
    pos_match = _YAHOO_POS.search(rest)
    if not pos_match:
        return None
    position = pos_match.group(1).replace("D/ST", "DST")
    name, team = _split_yahoo_name_team(rest[: pos_match.start()])
    if not name:
        return None
    return RankingRow(rank, name, team, position)


def parse_yahoo_pdf(path: Path) -> list[RankingRow]:
    """Parse Yahoo consensus top-300 exported as PDF (Half-PPR table)."""
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    rows: list[RankingRow] = []
    seen: set[int] = set()
    for line in text.splitlines():
        parsed = _parse_yahoo_pdf_line(line)
        if parsed is None or parsed.source_rank in seen:
            continue
        seen.add(parsed.source_rank)
        rows.append(parsed)
    rows.sort(key=lambda row: row.source_rank)
    return rows
