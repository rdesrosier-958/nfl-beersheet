"""NFL team abbreviations and aliases."""

from __future__ import annotations

ALIASES: dict[str, str] = {
    "ari": "ARI", "arizona": "ARI", "arizona cardinals": "ARI", "cardinals": "ARI",
    "atl": "ATL", "atlanta": "ATL", "atlanta falcons": "ATL", "falcons": "ATL",
    "bal": "BAL", "baltimore": "BAL", "baltimore ravens": "BAL", "ravens": "BAL",
    "buf": "BUF", "buffalo": "BUF", "buffalo bills": "BUF", "bills": "BUF",
    "car": "CAR", "carolina": "CAR", "carolina panthers": "CAR", "panthers": "CAR",
    "chi": "CHI", "chicago": "CHI", "chicago bears": "CHI", "bears": "CHI",
    "cin": "CIN", "cincinnati": "CIN", "cincinnati bengals": "CIN", "bengals": "CIN",
    "cle": "CLE", "cleveland": "CLE", "cleveland browns": "CLE", "browns": "CLE",
    "dal": "DAL", "dallas": "DAL", "dallas cowboys": "DAL", "cowboys": "DAL",
    "den": "DEN", "denver": "DEN", "denver broncos": "DEN", "broncos": "DEN",
    "det": "DET", "detroit": "DET", "detroit lions": "DET", "lions": "DET",
    "gb": "GB", "gnb": "GB", "green bay": "GB", "green bay packers": "GB", "packers": "GB",
    "hou": "HOU", "houston": "HOU", "houston texans": "HOU", "texans": "HOU",
    "ind": "IND", "indianapolis": "IND", "indianapolis colts": "IND", "colts": "IND",
    "jax": "JAX", "jac": "JAX", "jacksonville": "JAX", "jacksonville jaguars": "JAX", "jaguars": "JAX",
    "kc": "KC", "kan": "KC", "kansas city": "KC", "kansas city chiefs": "KC", "chiefs": "KC",
    "la": "LAR", "lar": "LAR", "los angeles r": "LAR", "los angeles rams": "LAR", "rams": "LAR",
    "lac": "LAC", "los angeles c": "LAC", "los angeles chargers": "LAC", "chargers": "LAC",
    "lv": "LV", "lvr": "LV", "las vegas": "LV", "las vegas raiders": "LV", "raiders": "LV",
    "mia": "MIA", "miami": "MIA", "miami dolphins": "MIA", "dolphins": "MIA",
    "min": "MIN", "minnesota": "MIN", "minnesota vikings": "MIN", "vikings": "MIN",
    "ne": "NE", "nwe": "NE", "new england": "NE", "new england patriots": "NE", "patriots": "NE",
    "no": "NO", "nor": "NO", "new orleans": "NO", "new orleans saints": "NO", "saints": "NO",
    "nyg": "NYG", "new york g": "NYG", "new york giants": "NYG", "giants": "NYG",
    "nyj": "NYJ", "new york j": "NYJ", "new york jets": "NYJ", "jets": "NYJ",
    "phi": "PHI", "philadelphia": "PHI", "philadelphia eagles": "PHI", "eagles": "PHI",
    "pit": "PIT", "pittsburgh": "PIT", "pittsburgh steelers": "PIT", "steelers": "PIT",
    "sea": "SEA", "seattle": "SEA", "seattle seahawks": "SEA", "seahawks": "SEA",
    "sf": "SF", "sfo": "SF", "san francisco": "SF", "san francisco 49ers": "SF", "49ers": "SF",
    "tb": "TB", "tampa bay": "TB", "tampa bay buccaneers": "TB", "buccaneers": "TB",
    "ten": "TEN", "tennessee": "TEN", "tennessee titans": "TEN", "titans": "TEN",
    "was": "WAS", "wsh": "WAS", "washington": "WAS", "washington commanders": "WAS", "commanders": "WAS",
}

CODES = set(ALIASES.values())


def canonical(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    if text.upper() in CODES:
        return text.upper()
    return ALIASES.get(text.lower())
