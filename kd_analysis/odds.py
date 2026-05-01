"""Odds conversions and overlay/underlay logic.

Fractional odds are stored as strings like "4-1" or "5/2". Decimal odds are
European-style (e.g. 4-1 -> 5.0, where stake is included in the payout).
Implied probability ignores track takeout, so the odds book will not sum to
1.0 — the gap is the bookmaker margin / overround.
"""

from __future__ import annotations

from typing import Iterable, Optional


def fractional_to_decimal(fractional: str) -> float:
    """Convert fractional odds like '4-1', '5/2', '7-2' to decimal.

    Decimal odds include the stake: 4-1 fractional == 5.0 decimal.
    """
    s = fractional.strip()
    sep = "-" if "-" in s else "/"
    if sep not in s:
        raise ValueError(f"Bad fractional odds: {fractional!r}")
    num_str, den_str = s.split(sep, 1)
    num, den = float(num_str), float(den_str)
    if den == 0:
        raise ValueError(f"Zero denominator in {fractional!r}")
    return num / den + 1.0


def implied_probability(fractional: str) -> float:
    """Return the bookmaker's implied probability for a fractional price."""
    return 1.0 / fractional_to_decimal(fractional)


def overlay_pct(ml: str, live: Optional[str]) -> Optional[float]:
    """Return percent overlay (positive) or underlay (negative) of live vs ML.

    Overlay means the live price is higher than morning line — the bettor
    gets more reward for the same implied probability. Returns None when no
    live price has been entered yet.

    Example:
        ml="4-1" (decimal 5.0), live="6-1" (decimal 7.0) -> +40.0% overlay
    """
    if live is None:
        return None
    ml_dec = fractional_to_decimal(ml)
    live_dec = fractional_to_decimal(live)
    return (live_dec - ml_dec) / ml_dec * 100.0


def book_overround(prices: Iterable[str]) -> float:
    """Sum of implied probabilities; values > 1 indicate bookmaker margin."""
    return sum(implied_probability(p) for p in prices)
