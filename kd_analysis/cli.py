"""Command-line entry: `kd odds <race>` and `kd tickets <race>`.

Race names are looked up under data/<race>_2026.yaml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kd_analysis.model import Race, load_race
from kd_analysis.odds import implied_probability, overlay_pct, book_overround
from kd_analysis.tickets import (
    Ticket,
    exacta_box,
    exacta_key,
    superfecta_key,
    trifecta_key,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(race_name: str) -> Race:
    path = DATA_DIR / f"{race_name}_2026.yaml"
    if not path.exists():
        sys.exit(f"No race data at {path}")
    return load_race(path)


def cmd_odds(args: argparse.Namespace) -> None:
    race = _load(args.race)
    print(f"\n{race.name} — {race.date} — {race.distance}")
    print(f"{'Post':<5}{'Horse':<22}{'ML':<8}{'Live':<8}{'Imp%':<7}{'Overlay':<10}{'Style':<6}")
    print("-" * 66)
    for h in race.horses:
        imp = implied_probability(h.ml) * 100
        ov = overlay_pct(h.ml, h.live_odds)
        ov_str = f"{ov:+.1f}%" if ov is not None else "—"
        live_str = h.live_odds or "—"
        print(
            f"{h.post:<5}{h.name[:21]:<22}{h.ml:<8}{live_str:<8}"
            f"{imp:<7.1f}{ov_str:<10}{h.style:<6}"
        )
    overround = book_overround(h.ml for h in race.horses) * 100
    print(f"\nML book overround: {overround:.1f}%  (>100% = bookmaker margin)")


def cmd_tickets(args: argparse.Namespace) -> None:
    race = _load(args.race)
    print(f"\n{race.name} — suggested tickets\n")

    if args.race == "oaks":
        tickets = _oaks_tickets()
    elif args.race == "derby":
        tickets = _derby_tickets()
    else:
        sys.exit(f"No default ticket plan for {args.race}")

    total = 0.0
    for t in tickets:
        print(t.describe())
        total += t.cost
    print(f"\nTotal cost: ${total:.2f}")


def _oaks_tickets() -> list[Ticket]:
    # Top tier: Zany (2), Meaning (5), Percy's Bar (9)
    # Underneath: Counting Stars (4), Always A Runner (7), Prom Queen (8), Explora (1)
    return [
        exacta_box([2, 5, 9], base=1.0),
        trifecta_key([2, 5, 9], [2, 5, 9], [1, 2, 4, 5, 7, 8, 9], base=0.5),
        superfecta_key(
            [2, 5, 9],
            [2, 5, 9],
            [1, 2, 4, 5, 7, 8, 9],
            [1, 2, 4, 5, 7, 8, 9],
            base=0.10,
        ),
    ]


def _derby_tickets() -> list[Ticket]:
    # Top tier: Renegade (1), Commandment (6), Chief Wallabee (12), Emerging Market (15)
    # Use: Further Ado (18), The Puma (9), Golden Tempo (19), So Happy (8)
    return [
        exacta_key(6, [1, 12, 15, 18], base=2.0),
        trifecta_key(
            [1, 6],
            [1, 6, 12, 15, 18],
            [1, 6, 8, 9, 12, 15, 18, 19],
            base=0.5,
        ),
        superfecta_key(
            [1, 6],
            [1, 6, 12, 15, 18],
            [1, 6, 8, 9, 12, 15, 18, 19],
            [1, 2, 6, 8, 9, 12, 15, 18, 19, 20],
            base=0.10,
        ),
        # Olczyk-overlay throw
        trifecta_key([6], [1, 15], [1, 12, 15, 19], base=1.0),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(prog="kd")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_odds = sub.add_parser("odds", help="Show odds table with overlay/underlay")
    p_odds.add_argument("race", choices=["oaks", "derby"])
    p_odds.set_defaults(func=cmd_odds)

    p_tix = sub.add_parser("tickets", help="Show suggested ticket structure + cost")
    p_tix.add_argument("race", choices=["oaks", "derby"])
    p_tix.set_defaults(func=cmd_tickets)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
