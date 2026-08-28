"""Paths and YAML config loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
LEAGUES_DIR = CONFIG_DIR / "leagues"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = DATA_DIR / "manual"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "output"

DEFAULT_LEAGUE_PROFILE = "espn-half-ppr"
_profile: str | None = None

for _d in (RAW_DIR, MANUAL_DIR, PROCESSED_DIR, OUTPUT_DIR, LEAGUES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def active_profile() -> str:
    return _profile or os.environ.get("NFL_LEAGUE", DEFAULT_LEAGUE_PROFILE)


def set_league(profile: str) -> None:
    global _profile
    path = LEAGUES_DIR / f"{profile}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"League profile not found: {path}")
    _profile = profile
    league.cache_clear()


def league_path() -> Path:
    path = LEAGUES_DIR / f"{active_profile()}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"League profile not found: {path}")
    return path


def output_dir() -> Path:
    path = OUTPUT_DIR / active_profile()
    path.mkdir(parents=True, exist_ok=True)
    return path


def projections_cache() -> Path:
    return PROCESSED_DIR / f"projections_{active_profile()}.pkl"


@lru_cache(maxsize=None)
def league() -> dict[str, Any]:
    return yaml.safe_load(league_path().read_text())


@lru_cache(maxsize=None)
def sources() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text())


def scoring() -> dict[str, Any]:
    return league()["scoring"]


def model() -> dict[str, Any]:
    return league()["model"]


def settings() -> dict[str, Any]:
    return league()["league"]
