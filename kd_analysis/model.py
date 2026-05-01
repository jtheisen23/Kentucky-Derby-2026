from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


VALID_STYLES = {"E", "EP", "P", "S"}


@dataclass
class Horse:
    post: int
    name: str
    ml: str
    jockey: str
    trainer: str
    style: str
    live_odds: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.style not in VALID_STYLES:
            raise ValueError(
                f"{self.name}: style {self.style!r} not in {sorted(VALID_STYLES)}"
            )


@dataclass
class Race:
    name: str
    date: str
    distance: str
    track: str
    horses: list[Horse]
    post_time_et: str = ""
    purse_usd: int = 0
    notes: str = ""

    def by_post(self, post: int) -> Horse:
        for h in self.horses:
            if h.post == post:
                return h
        raise KeyError(f"No horse at post {post}")

    def by_style(self, style: str) -> list[Horse]:
        return [h for h in self.horses if h.style == style]


def load_race(path: str | Path) -> Race:
    raw = yaml.safe_load(Path(path).read_text())
    horses = [Horse(**h) for h in raw.pop("horses")]
    raw["date"] = str(raw["date"])
    return Race(horses=horses, **raw)
