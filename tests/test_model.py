from pathlib import Path

import pytest

from kd_analysis.model import Horse, load_race

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_oaks_race():
    race = load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml")
    assert "Oaks" in race.name
    assert len(race.horses) == 13
    assert race.by_post(2).name == "Zany"


def test_load_derby_race():
    race = load_race(DATA / "derby_day" / "12_kentucky_derby.yaml")
    assert "Derby" in race.name
    assert len(race.horses) == 20
    assert race.by_post(1).name == "Renegade"
    assert race.by_post(18).name == "Further Ado"


def test_invalid_style_raises():
    with pytest.raises(ValueError):
        Horse(
            post=1,
            name="Bad",
            ml="4-1",
            jockey="x",
            trainer="x",
            style="X",
        )


def test_by_style_groups_horses():
    race = load_race(DATA / "derby_day" / "12_kentucky_derby.yaml")
    closers = race.by_style("S")
    assert any(h.name == "Renegade" for h in closers)


def test_by_post_missing_raises():
    race = load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml")
    with pytest.raises(KeyError):
        race.by_post(99)
