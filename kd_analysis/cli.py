"""Command-line entry: `kd odds <race>`, `kd tickets <race>`, `kd experts <race>`.

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


def _support_glyph(buckets: dict[str, list[str]]) -> str:
    """Compact glyph: T=top, U=use, L=longshot. Number = count of experts.

    Example: 'T2 U1' = 2 experts have it as top, 1 as use.
    """
    parts = []
    for code, key in (("T", "top"), ("U", "use"), ("L", "longshot")):
        n = len(buckets.get(key, []))
        if n:
            parts.append(f"{code}{n}")
    return " ".join(parts) if parts else "—"


def cmd_odds(args: argparse.Namespace) -> None:
    race = _load(args.race)
    print(f"\n{race.name} — {race.date} — {race.distance}")
    print(
        f"{'Post':<5}{'Horse':<22}{'ML':<8}{'Live':<8}{'Imp%':<7}"
        f"{'Overlay':<10}{'Style':<6}{'Score':<6}{'Experts':<10}"
    )
    print("-" * 88)
    for h in race.horses:
        imp = implied_probability(h.ml) * 100
        ov = overlay_pct(h.ml, h.live_odds)
        ov_str = f"{ov:+.1f}%" if ov is not None else "—"
        live_str = h.live_odds or "—"
        score = race.support_score(h.post)
        glyph = _support_glyph(race.expert_support(h.post))
        print(
            f"{h.post:<5}{h.name[:21]:<22}{h.ml:<8}{live_str:<8}"
            f"{imp:<7.1f}{ov_str:<10}{h.style:<6}{score:<6}{glyph:<10}"
        )
    overround = book_overround(h.ml for h in race.horses) * 100
    print(f"\nML book overround: {overround:.1f}%  (>100% = bookmaker margin)")
    if race.experts:
        confirmed = [e.name for e in race.experts if not e.tbd]
        tbd = [e.name for e in race.experts if e.tbd]
        if confirmed:
            print(f"Experts encoded: {', '.join(confirmed)}")
        if tbd:
            print(f"Experts pending picks: {', '.join(tbd)}")


def cmd_experts(args: argparse.Namespace) -> None:
    race = _load(args.race)
    print(f"\n{race.name} — expert picks\n")
    if not race.experts:
        print("(none)")
        return
    for e in race.experts:
        flag = " [TBD]" if e.tbd else ""
        print(f"=== {e.name} ({e.affiliation}){flag} ===")
        if e.top_picks:
            print(f"  Top:       {_format_horses(race, e.top_picks)}")
        if e.use_horses:
            print(f"  Use:       {_format_horses(race, e.use_horses)}")
        if e.longshots:
            print(f"  Longshots: {_format_horses(race, e.longshots)}")
        if e.notes:
            print(f"  Notes: {e.notes.strip()}")
        if e.source:
            print(f"  Source: {e.source}")
        print()

    print("Per-horse expert support (top=3, use=2, longshot=1):")
    ranked = sorted(race.horses, key=lambda h: race.support_score(h.post), reverse=True)
    for h in ranked:
        score = race.support_score(h.post)
        if score == 0:
            continue
        buckets = race.expert_support(h.post)
        details = []
        for code, key in (("top", "top"), ("use", "use"), ("longshot", "longshot")):
            if buckets[key]:
                details.append(f"{key}={','.join(buckets[key])}")
        print(f"  #{h.post:<2} {h.name:<22} score={score}  ({'; '.join(details)})")


def _format_horses(race: Race, posts: list[int]) -> str:
    return ", ".join(f"#{p} {race.by_post(p).name}" for p in posts)


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

    p_odds = sub.add_parser("odds", help="Show odds table with overlay/underlay + expert support")
    p_odds.add_argument("race", choices=["oaks", "derby"])
    p_odds.set_defaults(func=cmd_odds)

    p_tix = sub.add_parser("tickets", help="Show suggested ticket structure + cost")
    p_tix.add_argument("race", choices=["oaks", "derby"])
    p_tix.set_defaults(func=cmd_tickets)

    p_exp = sub.add_parser("experts", help="Show per-expert picks and per-horse support")
    p_exp.add_argument("race", choices=["oaks", "derby"])
    p_exp.set_defaults(func=cmd_experts)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
