from pathlib import Path

from kd_analysis.model import load_card

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_oaks_card():
    card = load_card(DATA / "oaks_day")
    assert card.name == "2026 Kentucky Oaks Day"
    assert card.date == "2026-05-01"
    assert len(card.races) == 13
    # Race 13 should be the Kentucky Oaks itself
    last = card.races[-1]
    assert last.number == 13
    assert "Kentucky Oaks" in last.race.name
    assert last.field_status == "full"


def test_load_derby_card():
    card = load_card(DATA / "derby_day")
    assert card.name == "2026 Kentucky Derby Day"
    assert len(card.races) == 14
    derby = next(cr for cr in card.races if cr.number == 12)
    assert "Kentucky Derby" in derby.race.name
    assert derby.field_status == "full"


def test_card_stakes_filter():
    card = load_card(DATA / "oaks_day")
    stakes = card.stakes
    # Edgewood, Twin Spires Turf Sprint, Eight Belles, La Troienne, Modesty,
    # Alysheba, Kentucky Oaks = 7 graded stakes
    assert len(stakes) == 7
    assert all(cr.grade for cr in stakes)


def test_card_marquee_returns_oaks():
    card = load_card(DATA / "oaks_day")
    marquee = card.marquee
    assert marquee is not None
    assert "Kentucky Oaks" in marquee.race.name


def test_card_marquee_returns_derby():
    card = load_card(DATA / "derby_day")
    marquee = card.marquee
    assert marquee is not None
    assert "Kentucky Derby" in marquee.race.name


def test_skeleton_races_have_empty_horses():
    card = load_card(DATA / "oaks_day")
    skel = [cr for cr in card.races if cr.field_status == "skeleton"]
    assert skel  # at least one
    assert all(cr.race.horses == [] for cr in skel)


def test_races_sorted_by_number():
    card = load_card(DATA / "derby_day")
    nums = [cr.number for cr in card.races]
    assert nums == sorted(nums)
