from pathlib import Path

import pytest

from kd_analysis.model import load_race
from kd_analysis.preview import (
    consensus,
    longshot_watch,
    pace_shape,
    value_flags,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def test_pace_shape_derby_speed_count():
    race = load_race(DATA / "derby_2026.yaml")
    shape = pace_shape(race)
    # YAML has So Happy, Potente, Pavlovian, Six Speed as 'E' (4 pure speeds)
    assert shape.counts["E"] == 4


def test_pace_shape_derby_projection_mentions_closers():
    race = load_race(DATA / "derby_2026.yaml")
    shape = pace_shape(race)
    # 4 speeds -> contested fractions, favors closers
    assert "closers" in shape.projection.lower()


def test_pace_shape_oaks_balanced():
    race = load_race(DATA / "oaks_2026.yaml")
    shape = pace_shape(race)
    # Oaks has 1 'E' (Dazzling Dame) so projection is the lone-speed branch
    assert shape.counts["E"] == 1
    assert "lone speed" in shape.projection.lower()


def test_pace_shape_lines_include_horse_names():
    race = load_race(DATA / "derby_2026.yaml")
    text = "\n".join(pace_shape(race).lines())
    assert "Renegade" in text  # closer
    assert "Pavlovian" in text  # speed


def test_consensus_orders_by_score():
    race = load_race(DATA / "derby_2026.yaml")
    rows = consensus(race)
    assert rows[0].horse.post == 1  # Renegade has score 5
    assert rows[0].score == 5
    # All returned horses have nonzero score
    assert all(r.score > 0 for r in rows)


def test_value_flags_finds_longer_prices_with_support():
    race = load_race(DATA / "derby_2026.yaml")
    rows = value_flags(race, min_score=2, min_price=8.0)
    posts = {r.horse.post for r in rows}
    # Emerging Market (#15, 15-1, score 3), Chief Wallabee (#12, 8-1, score 3),
    # Incredibolt (#11, 20-1, score 2) qualify
    assert 15 in posts
    assert 11 in posts
    # Renegade (4-1) is too short to be a value flag
    assert 1 not in posts


def test_longshot_watch_includes_olczyk_pick():
    race = load_race(DATA / "derby_2026.yaml")
    rows = longshot_watch(race)
    posts = {r.horse.post for r in rows}
    # Golden Tempo (#19) is Olczyk's longshot
    assert 19 in posts


def test_oaks_consensus_empty_when_all_tbd():
    race = load_race(DATA / "oaks_2026.yaml")
    # All Oaks experts are TBD, so no horse has any score
    assert consensus(race) == []
    assert value_flags(race) == []
    assert longshot_watch(race) == []
