"""Exotic ticket builders with combination counts and cost.

Pari-mutuel exotics are priced per combination. A "box" includes every
ordering of the selected horses. A "key" forces one or more horses into a
specific finishing slot and combines the remaining slots from a separate
pool.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Sequence


@dataclass
class Ticket:
    label: str
    bet_type: str
    base: float
    combinations: int

    @property
    def cost(self) -> float:
        return self.base * self.combinations

    def describe(self) -> str:
        return (
            f"{self.label}: {self.bet_type}, "
            f"{self.combinations} combos × ${self.base:.2f} = ${self.cost:.2f}"
        )


def _check_distinct(*groups: Sequence[int]) -> None:
    flat = [p for g in groups for p in g]
    if len(set(flat)) != len({(i, p) for i, g in enumerate(groups) for p in g}):
        # allow same horse in different slots (key tickets) but reject dupes inside one group
        for g in groups:
            if len(set(g)) != len(g):
                raise ValueError(f"Duplicate post in group: {g}")


def exacta_box(posts: Sequence[int], base: float = 1.0) -> Ticket:
    """All ordered pairs of N horses → N*(N-1) combos."""
    _check_distinct(posts)
    n = len(posts)
    if n < 2:
        raise ValueError("Exacta box needs at least 2 horses")
    combos = n * (n - 1)
    return Ticket(f"Exacta box {sorted(posts)}", "exacta", base, combos)


def exacta_key(key: int, with_posts: Sequence[int], base: float = 1.0) -> Ticket:
    """Key horse on top, any of `with_posts` 2nd. Combos = len(with_posts)."""
    if key in with_posts:
        with_posts = [p for p in with_posts if p != key]
    if not with_posts:
        raise ValueError("Exacta key needs at least one 'with' horse")
    combos = len(with_posts)
    return Ticket(
        f"Exacta key {key} OVER {sorted(with_posts)}", "exacta", base, combos
    )


def trifecta_key(
    first: Sequence[int],
    second: Sequence[int],
    third: Sequence[int],
    base: float = 0.5,
) -> Ticket:
    """Trifecta with separate pools per slot. Counts only valid orderings
    (no horse used twice in the same triple).
    """
    for g in (first, second, third):
        if not g:
            raise ValueError("All three slots need at least one horse")
    combos = sum(
        1
        for a in first
        for b in second
        for c in third
        if len({a, b, c}) == 3
    )
    if combos == 0:
        raise ValueError("No valid trifecta combinations across the three slots")
    return Ticket(
        f"Trifecta {sorted(first)} / {sorted(second)} / {sorted(third)}",
        "trifecta",
        base,
        combos,
    )


def superfecta_key(
    first: Sequence[int],
    second: Sequence[int],
    third: Sequence[int],
    fourth: Sequence[int],
    base: float = 0.10,
) -> Ticket:
    for g in (first, second, third, fourth):
        if not g:
            raise ValueError("All four slots need at least one horse")
    combos = sum(
        1
        for a in first
        for b in second
        for c in third
        for d in fourth
        if len({a, b, c, d}) == 4
    )
    if combos == 0:
        raise ValueError("No valid superfecta combinations across the four slots")
    return Ticket(
        f"Super {sorted(first)} / {sorted(second)} / {sorted(third)} / {sorted(fourth)}",
        "superfecta",
        base,
        combos,
    )


def trifecta_box(posts: Sequence[int], base: float = 0.5) -> Ticket:
    n = len(posts)
    if n < 3:
        raise ValueError("Trifecta box needs at least 3 horses")
    combos = sum(1 for _ in permutations(posts, 3))
    return Ticket(f"Trifecta box {sorted(posts)}", "trifecta", base, combos)
