"""Fetch source pages and cache them on disk."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import requests

from . import config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Fetched:
    source_id: str
    path: Path
    html: str
    fetched_at: str
    from_cache: bool


def _dir_for(source_id: str) -> Path:
    directory = config.RAW_DIR / source_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def latest_cached(source_id: str) -> Path | None:
    directory = _dir_for(source_id)
    files = sorted(directory.glob("*.html"))
    return files[-1] if files else None


def fetch(source_id: str, url: str, *, offline: bool = False, timeout: int = 30) -> Fetched | None:
    today = dt.date.today().isoformat()
    target = _dir_for(source_id) / f"{today}.html"

    if offline or (target.exists() and _fresh_enough(target)):
        cached = target if target.exists() else latest_cached(source_id)
        if cached:
            return Fetched(
                source_id, cached, cached.read_text(errors="ignore"),
                _stamp(cached), from_cache=True,
            )
        if offline:
            return None

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        cached = latest_cached(source_id)
        if cached:
            print(f"  ! {source_id}: {type(exc).__name__}; using cache from {_stamp(cached)}")
            return Fetched(
                source_id, cached, cached.read_text(errors="ignore"),
                _stamp(cached), from_cache=True,
            )
        print(f"  ! {source_id}: {type(exc).__name__} and no cache available")
        return None

    target.write_text(response.text)
    _prune(_dir_for(source_id))
    return Fetched(source_id, target, response.text, today, from_cache=False)


def _fresh_enough(path: Path) -> bool:
    return path.stem == dt.date.today().isoformat()


def _stamp(path: Path) -> str:
    return path.stem


def _prune(directory: Path, keep: int = 5) -> None:
    files = sorted(directory.glob("*.html"))
    for old in files[:-keep]:
        old.unlink(missing_ok=True)
