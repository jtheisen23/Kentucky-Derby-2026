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
class Expert:
    """A handicapper's published picks for the race.

    Posts are stored as integers referring to Horse.post. The same horse can
    appear in more than one bucket (a top pick can also be a key-and-use).
    `tbd=True` means the expert is on record covering the race but their
    specific selections were not retrievable when the data file was built.
    """

    name: str
    affiliation: str
    top_picks: list[int] = field(default_factory=list)
    use_horses: list[int] = field(default_factory=list)
    longshots: list[int] = field(default_factory=list)
    source: str = ""
    notes: str = ""
    tbd: bool = False

    def supports(self, post: int) -> set[str]:
        """Return the set of buckets ({'top','use','longshot'}) this expert
        has the given horse in. Empty set means no endorsement.
        """
        out: set[str] = set()
        if post in self.top_picks:
            out.add("top")
        if post in self.use_horses:
            out.add("use")
        if post in self.longshots:
            out.add("longshot")
        return out


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
    experts: list[Expert] = field(default_factory=list)

    def by_post(self, post: int) -> Horse:
        for h in self.horses:
            if h.post == post:
                return h
        raise KeyError(f"No horse at post {post}")

    def by_style(self, style: str) -> list[Horse]:
        return [h for h in self.horses if h.style == style]

    def expert_support(self, post: int) -> dict[str, list[str]]:
        """Map bucket name -> list of expert names backing this post."""
        out: dict[str, list[str]] = {"top": [], "use": [], "longshot": []}
        for e in self.experts:
            for bucket in e.supports(post):
                out[bucket].append(e.name)
        return out

    def support_score(self, post: int) -> int:
        """Weighted score: top=3, use=2, longshot=1. Used for quick ranking."""
        weights = {"top": 3, "use": 2, "longshot": 1}
        s = self.expert_support(post)
        return sum(weights[b] * len(names) for b, names in s.items())


def load_race(path: str | Path) -> Race:
    raw = yaml.safe_load(Path(path).read_text())
    horses = [Horse(**h) for h in raw.pop("horses")]
    experts_raw = raw.pop("experts", []) or []
    experts = [Expert(**e) for e in experts_raw]
    raw["date"] = str(raw["date"])
    return Race(horses=horses, experts=experts, **raw)
