"""Paths and YAML config loading."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = DATA_DIR / "manual"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "output"

for _d in (RAW_DIR, MANUAL_DIR, PROCESSED_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=None)
def league() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "league.yaml").read_text())


@lru_cache(maxsize=None)
def sources() -> dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text())


def scoring() -> dict[str, Any]:
    return league()["scoring"]


def model() -> dict[str, Any]:
    return league()["model"]


def settings() -> dict[str, Any]:
    return league()["league"]
