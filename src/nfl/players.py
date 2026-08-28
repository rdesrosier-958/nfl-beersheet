"""Player identity and cross-source merging."""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

from . import teams

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
_ROMAN = {"ii", "iii", "iv", "v"}
_PUNCT = re.compile(r"[^a-z0-9 ]+")
POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}


def name_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = text.lower().replace("-", " ").replace(".", "")
    text = _PUNCT.sub("", text)
    parts = [p for p in text.split() if p and p not in SUFFIXES]
    return " ".join(parts)


def _significant_tokens(name: str) -> list[str]:
    return [p for p in name_key(name).split() if p not in _ROMAN]


def normalise_position(raw: str, name: str = "") -> str | None:
    text = (raw or "").upper().strip()
    if text in {"D/ST", "DEF", "DEFENSE"}:
        return "DST"
    if text in POSITIONS:
        return text
    if text in {"K", "PK"}:
        return "K"
    return None


@dataclass
class Player:
    name: str
    position: str
    team: str
    key: str
    source_ranks: dict[str, int] = field(default_factory=dict)
    source_pos_ranks: dict[str, int] = field(default_factory=dict)
    source_overall_ranks: dict[str, int] = field(default_factory=dict)
    stats: dict[str, float] = field(default_factory=dict)
    stat_source: str = ""
    espn_points: float | None = None
    bye: int | None = None
    subvertadown_val: float | None = None
    subvertadown_adp: float | None = None


class Registry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], Player] = {}

    def all(self) -> list[Player]:
        return list(self._by_key.values())

    def add(
        self,
        *,
        name: str,
        team_raw: str,
        position: str,
        source_id: str,
        rank: int,
        pos_rank: int | None = None,
    ) -> Player | None:
        resolved = normalise_position(position, name)
        if resolved is None:
            return None
        team = teams.canonical(team_raw) or (team_raw or "").strip()
        key = name_key(name)
        lookup = (key, resolved)
        player = self._by_key.get(lookup)
        if player is None:
            player = Player(name=name.strip(), position=resolved, team=team, key=key)
            self._by_key[lookup] = player
        elif team and not player.team:
            player.team = team
        player.source_ranks[source_id] = rank
        if pos_rank is not None:
            player.source_pos_ranks[source_id] = pos_rank
        player.source_overall_ranks[source_id] = rank
        return player

    def find(self, name: str, position: str) -> Player | None:
        resolved = normalise_position(position, name)
        if resolved is None:
            return None
        exact = self._by_key.get((name_key(name), resolved))
        if exact:
            return exact
        candidates = [p for p in self._by_key.values() if p.position == resolved]
        matches = difflib.get_close_matches(name_key(name), [p.key for p in candidates], n=1, cutoff=0.92)
        if not matches:
            return None
        return next(p for p in candidates if p.key == matches[0])

    def match_abbreviated(self, short_name: str, team: str, position: str) -> Player | None:
        """Match Yahoo-style abbreviated names (e.g. J. Gibbs) to full ESPN names."""
        resolved = normalise_position(position, short_name)
        if resolved is None:
            return None

        tokens = _significant_tokens(short_name)
        if not tokens:
            return None

        pool = [p for p in self._by_key.values() if p.position == resolved]
        if team:
            by_team = [p for p in pool if p.team == team]
            if by_team:
                pool = by_team

        if resolved == "DST" and team:
            for player in pool:
                if team in player.name.upper():
                    return player

        last = tokens[-1]
        for player in pool:
            parts = _significant_tokens(player.name)
            if not parts:
                continue
            if last == parts[-1] or last in parts:
                return player
            if parts[-1].startswith(last) or last.startswith(parts[-1]):
                return player

        return self.find(short_name, resolved)

    def add_yahoo_rank(
        self,
        *,
        short_name: str,
        team_raw: str,
        position: str,
        source_id: str,
        rank: int,
    ) -> Player | None:
        team = teams.canonical(team_raw) or (team_raw or "").strip()
        player = self.match_abbreviated(short_name, team, position)
        if player is None:
            player = self.add(
                name=short_name, team_raw=team, position=position,
                source_id=source_id, rank=rank,
            )
            return player
        player.source_ranks[source_id] = rank
        player.source_overall_ranks[source_id] = rank
        if team and not player.team:
            player.team = team
        return player
