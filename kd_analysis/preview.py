"""Race preview synthesis.

Pulls together pace shape, expert consensus, value flags, and longshot
watch from a Race object. Returns plain strings so the CLI can print them
and tests can assert on the content.
"""

from __future__ import annotations

from dataclasses import dataclass

from kd_analysis.model import Horse, Race
from kd_analysis.odds import implied_probability


STYLE_LABEL = {
    "E": "front-runner",
    "EP": "forward / presser",
    "P": "stalker",
    "S": "closer",
}


@dataclass
class PaceShape:
    counts: dict[str, int]
    horses_by_style: dict[str, list[Horse]]
    projection: str

    def lines(self) -> list[str]:
        out = ["PACE SHAPE"]
        for code in ("E", "EP", "P", "S"):
            n = self.counts.get(code, 0)
            if not n:
                continue
            names = ", ".join(h.name for h in self.horses_by_style[code])
            out.append(f"  {n} {STYLE_LABEL[code]} ({code}): {names}")
        out.append(f"  -> {self.projection}")
        return out


def pace_shape(race: Race) -> PaceShape:
    counts: dict[str, int] = {}
    horses_by_style: dict[str, list[Horse]] = {"E": [], "EP": [], "P": [], "S": []}
    for h in race.horses:
        counts[h.style] = counts.get(h.style, 0) + 1
        horses_by_style[h.style].append(h)

    e = counts.get("E", 0)
    ep = counts.get("EP", 0)
    s = counts.get("S", 0)

    if e >= 3:
        projection = (
            f"{e} pure speeds projects contested fractions; "
            "favors stalkers and closers"
        )
    elif e == 0:
        projection = "no pure speed; lone forward types may steal it on the lead"
    elif e == 1:
        projection = (
            "lone speed scenario; the front-runner can dictate slow fractions"
        )
    else:  # e == 2
        projection = (
            f"{e} speeds with {ep} forward types; honest pace, "
            "no full meltdown — balanced setup"
        )
    if s >= 5 and e >= 2:
        projection += f"; deep closer pool ({s}) sharpens late kick"
    return PaceShape(counts=counts, horses_by_style=horses_by_style, projection=projection)


@dataclass
class Contender:
    horse: Horse
    score: int
    imp_pct: float


def consensus(race: Race, top_n: int = 8) -> list[Contender]:
    rows = [
        Contender(
            horse=h,
            score=race.support_score(h.post),
            imp_pct=implied_probability(h.ml) * 100,
        )
        for h in race.horses
    ]
    rows.sort(key=lambda r: (-r.score, -r.imp_pct))
    return [r for r in rows[:top_n] if r.score > 0]


def value_flags(race: Race, min_score: int = 2, min_price: float = 8.0) -> list[Contender]:
    """Horses with expert support but a longer ML price.

    `min_price` is the fractional numerator threshold (e.g. 8.0 == 8-1 or longer).
    """
    out = []
    for h in race.horses:
        score = race.support_score(h.post)
        if score < min_score:
            continue
        num_str = h.ml.replace("/", "-").split("-")[0]
        try:
            num = float(num_str)
        except ValueError:
            continue
        if num >= min_price:
            out.append(
                Contender(
                    horse=h,
                    score=score,
                    imp_pct=implied_probability(h.ml) * 100,
                )
            )
    out.sort(key=lambda r: (-r.score, -float(r.horse.ml.split("-")[0])))
    return out


def longshot_watch(race: Race) -> list[Contender]:
    """Any horse flagged as 'longshot' by at least one expert, plus
    high-price horses (20-1+) with any support.
    """
    out: list[Contender] = []
    seen: set[int] = set()
    for h in race.horses:
        score = race.support_score(h.post)
        is_longshot_pick = any(
            h.post in e.longshots for e in race.experts
        )
        try:
            num = float(h.ml.split("-")[0])
        except ValueError:
            num = 0.0
        if is_longshot_pick or (num >= 20 and score >= 1):
            if h.post in seen:
                continue
            seen.add(h.post)
            out.append(
                Contender(
                    horse=h,
                    score=score,
                    imp_pct=implied_probability(h.ml) * 100,
                )
            )
    return out
