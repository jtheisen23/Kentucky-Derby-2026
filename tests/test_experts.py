from pathlib import Path

import pytest

from kd_analysis.model import Expert, load_race

DATA = Path(__file__).resolve().parent.parent / "data"


def test_expert_supports_buckets():
    e = Expert(
        name="X",
        affiliation="Y",
        top_picks=[1, 2],
        use_horses=[3],
        longshots=[4],
    )
    assert e.supports(1) == {"top"}
    assert e.supports(3) == {"use"}
    assert e.supports(4) == {"longshot"}
    assert e.supports(99) == set()


def test_expert_can_be_in_multiple_buckets():
    e = Expert(name="X", affiliation="Y", top_picks=[1], use_horses=[1])
    assert e.supports(1) == {"top", "use"}


def test_derby_loads_three_experts():
    race = load_race(DATA / "derby_2026.yaml")
    names = [e.name for e in race.experts]
    assert "Eddie Olczyk" in names
    assert "Randy Moss" in names
    assert "Mike Somich" in names


def test_olczyk_derby_picks_intact():
    race = load_race(DATA / "derby_2026.yaml")
    olczyk = next(e for e in race.experts if e.name == "Eddie Olczyk")
    # Emerging Market top, Renegade use, Golden Tempo longshot
    assert olczyk.top_picks == [15]
    assert 1 in olczyk.use_horses
    assert 19 in olczyk.longshots
    assert olczyk.tbd is False


def test_moss_derby_top_five():
    race = load_race(DATA / "derby_2026.yaml")
    moss = next(e for e in race.experts if e.name == "Randy Moss")
    # Top-5 narrowed: Commandment(6), Further Ado(18), Renegade(1), The Puma(9), Chief Wallabee(12)
    assert set(moss.top_picks) == {1, 6, 9, 12, 18}
    assert moss.tbd is False


def test_somich_derby_marked_tbd():
    race = load_race(DATA / "derby_2026.yaml")
    somich = next(e for e in race.experts if e.name == "Mike Somich")
    assert somich.tbd is True
    # No fabricated picks
    assert somich.top_picks == []


def test_oaks_experts_all_tbd():
    race = load_race(DATA / "oaks_2026.yaml")
    assert len(race.experts) == 3
    assert all(e.tbd for e in race.experts)


def test_support_score_weighting():
    race = load_race(DATA / "derby_2026.yaml")
    # Renegade (#1): Olczyk has it as 'use' (2), Moss has it as 'top' (3) = 5
    assert race.support_score(1) == 5
    # Emerging Market (#15): Olczyk top (3) = 3
    assert race.support_score(15) == 3
    # Commandment (#6): Moss top (3) = 3
    assert race.support_score(6) == 3
    # Golden Tempo (#19): Olczyk longshot (1) = 1
    assert race.support_score(19) == 1
    # Albus (#2): nobody = 0
    assert race.support_score(2) == 0


def test_expert_support_returns_names():
    race = load_race(DATA / "derby_2026.yaml")
    support = race.expert_support(1)  # Renegade
    assert "Eddie Olczyk" in support["use"]
    assert "Randy Moss" in support["top"]
