import pytest

from kd_analysis.tickets import (
    exacta_box,
    exacta_key,
    superfecta_key,
    trifecta_box,
    trifecta_key,
)


def test_exacta_box_3_horses():
    t = exacta_box([1, 2, 3], base=1.0)
    # 3 * 2 = 6 ordered pairs
    assert t.combinations == 6
    assert t.cost == pytest.approx(6.0)


def test_exacta_box_4_horses():
    t = exacta_box([1, 2, 3, 4], base=2.0)
    assert t.combinations == 12
    assert t.cost == pytest.approx(24.0)


def test_exacta_box_too_few_horses():
    with pytest.raises(ValueError):
        exacta_box([1])


def test_exacta_key_drops_duplicate():
    # Key 1 with [1, 2, 3] should drop the duplicate
    t = exacta_key(1, [1, 2, 3], base=1.0)
    assert t.combinations == 2


def test_trifecta_key_basic():
    # 1 / 2,3 / 4,5 -> 4 valid combos (1-2-4, 1-2-5, 1-3-4, 1-3-5)
    t = trifecta_key([1], [2, 3], [4, 5], base=0.5)
    assert t.combinations == 4
    assert t.cost == pytest.approx(2.0)


def test_trifecta_key_overlap():
    # 1,2 / 1,2,3 / 1,2,3,4 — must dedupe per ordering
    t = trifecta_key([1, 2], [1, 2, 3], [1, 2, 3, 4])
    # Manually: count orderings where all three differ
    expected = sum(
        1
        for a in [1, 2]
        for b in [1, 2, 3]
        for c in [1, 2, 3, 4]
        if len({a, b, c}) == 3
    )
    assert t.combinations == expected


def test_trifecta_box_3_horses():
    t = trifecta_box([1, 2, 3])
    assert t.combinations == 6  # 3!


def test_trifecta_box_4_horses():
    t = trifecta_box([1, 2, 3, 4])
    assert t.combinations == 24  # 4*3*2


def test_superfecta_key_basic():
    # 1 / 2 / 3 / 4 -> exactly 1 combo
    t = superfecta_key([1], [2], [3], [4])
    assert t.combinations == 1


def test_superfecta_key_realistic():
    # 1,6 / 1,6,12,15,18 / ... matches the Derby sample structure
    t = superfecta_key(
        [1, 6],
        [1, 6, 12, 15, 18],
        [1, 6, 8, 9, 12, 15, 18, 19],
        [1, 2, 6, 8, 9, 12, 15, 18, 19, 20],
        base=0.10,
    )
    assert t.combinations > 0
    # Cost should be reasonable
    assert 30 < t.cost < 100


def test_ticket_describe_includes_label():
    t = exacta_box([1, 2, 3])
    assert "Exacta box" in t.describe()
    assert "$6.00" in t.describe()
