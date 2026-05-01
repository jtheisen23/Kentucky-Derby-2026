from pathlib import Path

import pytest

from kd_analysis.model import load_race
from kd_analysis.render import render_index, render_race, write_site
from kd_analysis.tickets import exacta_box, trifecta_key

DATA = Path(__file__).resolve().parent.parent / "data"


def test_render_race_oaks_includes_key_content():
    race = load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml")
    html = render_race(race, [exacta_box([2, 5, 9])])
    assert "<!doctype html>" in html
    assert "Kentucky Oaks" in html
    assert "Zany" in html
    assert "Pace shape" in html
    assert "Public Consensus" in html


def test_render_race_derby_includes_consensus_and_tickets():
    race = load_race(DATA / "derby_day" / "12_kentucky_derby.yaml")
    html = render_race(
        race,
        [trifecta_key([1, 6], [1, 6, 12, 15], [1, 6, 12, 15])],
    )
    assert "Renegade" in html
    assert "Suggested tickets" in html
    assert "Trifecta" in html
    assert "Expert consensus" in html


def test_render_index_links_both_races():
    oaks = load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml")
    derby = load_race(DATA / "derby_day" / "12_kentucky_derby.yaml")
    html = render_index([("oaks", oaks), ("derby", derby)])
    assert 'href="oaks.html"' in html
    assert 'href="derby.html"' in html


def test_render_escapes_user_content(tmp_path):
    """Make sure HTML escaping is applied so YAML data can't inject markup."""
    race = load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml")
    # Inject a malicious-looking name and re-render
    race.horses[0].name = "<script>alert(1)</script>"
    html = render_race(race, [])
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_write_site_creates_files(tmp_path):
    races = {
        "oaks": load_race(DATA / "oaks_day" / "13_kentucky_oaks.yaml"),
        "derby": load_race(DATA / "derby_day" / "12_kentucky_derby.yaml"),
    }
    suggestions: dict = {"oaks": [], "derby": []}
    written = write_site(tmp_path, races, suggestions)
    paths = {p.name for p in written}
    assert "index.html" in paths
    assert "oaks.html" in paths
    assert "derby.html" in paths
    assert ".nojekyll" in paths
    assert (tmp_path / "index.html").read_text().startswith("<!doctype html>")
