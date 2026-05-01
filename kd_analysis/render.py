"""Static HTML renderer for race previews.

Produces a self-contained HTML page per race and an index. No template
engine, no JS — inline CSS only so the output is trivially deployable to
GitHub Pages.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from kd_analysis.model import Card, CardRace, Expert, Race
from kd_analysis.odds import implied_probability, overlay_pct
from kd_analysis.preview import (
    STYLE_LABEL,
    consensus,
    longshot_watch,
    pace_shape,
    value_flags,
)


CSS = """
:root {
  --bg: #fafaf7; --fg: #1a1a1a; --muted: #6b6b6b; --line: #e2e2dd;
  --accent: #8b1538; --card: #ffffff; --good: #1f7a3a; --warn: #b85c00;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15161a; --fg: #ececec; --muted: #9a9a9a; --line: #2a2a30;
    --accent: #d96a8a; --card: #1c1d22; --good: #4cb87a; --warn: #e69e4d;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.container { max-width: 960px; margin: 0 auto; padding: 1.5rem 1rem 4rem; }
header.site { border-bottom: 1px solid var(--line); margin-bottom: 1.5rem; padding-bottom: 1rem; }
header.site h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
header.site p { margin: 0; color: var(--muted); }
nav { margin: 1rem 0; }
nav a {
  display: inline-block; margin-right: .75rem; padding: .35rem .75rem;
  border: 1px solid var(--line); border-radius: 999px;
  text-decoration: none; color: var(--fg); font-size: .9rem;
}
nav a:hover { border-color: var(--accent); color: var(--accent); }
h2 {
  font-size: 1.1rem; text-transform: uppercase; letter-spacing: .05em;
  border-bottom: 1px solid var(--line); padding-bottom: .35rem; margin: 2rem 0 .75rem;
}
h3 { font-size: 1rem; margin: 1.25rem 0 .5rem; }
.meta { color: var(--muted); font-size: .9rem; margin-bottom: 1rem; }
.cards { display: grid; gap: .75rem; grid-template-columns: 1fr; }
@media (min-width: 640px) { .cards { grid-template-columns: repeat(2, 1fr); } }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: .85rem 1rem;
}
.card .name { font-weight: 600; }
.card .post { color: var(--accent); font-weight: 700; margin-right: .35rem; }
.card .ml { color: var(--muted); font-size: .9rem; }
.card .note { font-size: .85rem; color: var(--muted); margin-top: .35rem; }
.tag { display: inline-block; font-size: .72rem; padding: 1px 6px; border-radius: 4px; margin-right: .25rem;
       border: 1px solid var(--line); }
.tag.top { color: var(--good); border-color: var(--good); }
.tag.use { color: var(--warn); border-color: var(--warn); }
.tag.longshot { color: var(--accent); border-color: var(--accent); }
table {
  width: 100%; border-collapse: collapse; font-size: .92rem; margin-top: .5rem;
}
th, td {
  text-align: left; padding: .4rem .5rem; border-bottom: 1px solid var(--line);
  vertical-align: top;
}
th { font-weight: 600; color: var(--muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.pace-line { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: .9rem; }
.proj { background: var(--card); border-left: 3px solid var(--accent); padding: .5rem .75rem; margin-top: .5rem; }
.expert {
  background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: .85rem 1rem; margin-bottom: .75rem;
}
.expert h3 { margin-top: 0; }
.expert .pending { color: var(--warn); font-size: .8rem; margin-left: .35rem; }
.expert .picks { font-size: .9rem; }
.expert .notes { color: var(--muted); font-size: .85rem; margin-top: .5rem; white-space: pre-wrap; }
.expert a { color: var(--accent); }
footer { color: var(--muted); font-size: .8rem; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--line); }
"""


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _race_title(race: Race) -> str:
    return _esc(race.name)


def _meta(race: Race) -> str:
    bits = [_esc(race.date)]
    if race.post_time_et:
        bits.append(f"{_esc(race.post_time_et)} ET")
    bits.extend([_esc(race.track), _esc(race.distance)])
    if race.purse_usd:
        bits.append(f"${race.purse_usd:,}")
    bits.append(f"{len(race.horses)} horses")
    return " &middot; ".join(bits)


def _pace_section(race: Race) -> str:
    shape = pace_shape(race)
    rows = []
    for code in ("E", "EP", "P", "S"):
        n = shape.counts.get(code, 0)
        if not n:
            continue
        names = ", ".join(_esc(h.name) for h in shape.horses_by_style[code])
        rows.append(
            f"<div class='pace-line'><strong>{n}</strong> "
            f"{_esc(STYLE_LABEL[code])} ({code}): {names}</div>"
        )
    return (
        "<h2>Pace shape</h2>"
        + "".join(rows)
        + f"<div class='proj'><strong>Projection:</strong> {_esc(shape.projection)}</div>"
    )


def _support_tags(race: Race, post: int) -> str:
    s = race.expert_support(post)
    parts = []
    for bucket in ("top", "use", "longshot"):
        for name in s.get(bucket, []):
            parts.append(
                f"<span class='tag {bucket}'>{_esc(bucket)}: {_esc(name)}</span>"
            )
    return "".join(parts)


def _consensus_section(race: Race) -> str:
    rows = consensus(race)
    if not rows:
        return ""
    body = []
    for c in rows:
        body.append(
            "<div class='card'>"
            f"<div><span class='post'>#{c.horse.post}</span>"
            f"<span class='name'>{_esc(c.horse.name)}</span> "
            f"<span class='ml'>{_esc(c.horse.ml)} &middot; {c.imp_pct:.1f}% imp &middot; score {c.score}</span></div>"
            f"<div>{_support_tags(race, c.horse.post)}</div>"
            "</div>"
        )
    return (
        "<h2>Expert consensus</h2>"
        f"<div class='cards'>{''.join(body)}</div>"
    )


def _value_section(race: Race) -> str:
    rows = value_flags(race)
    if not rows:
        return ""
    body = []
    for v in rows:
        first_note = (v.horse.notes.splitlines()[0] if v.horse.notes else "").strip()
        body.append(
            "<div class='card'>"
            f"<div><span class='post'>#{v.horse.post}</span>"
            f"<span class='name'>{_esc(v.horse.name)}</span> "
            f"<span class='ml'>{_esc(v.horse.ml)} &middot; {v.imp_pct:.1f}% imp &middot; score {v.score}</span></div>"
            + (f"<div class='note'>{_esc(first_note)}</div>" if first_note else "")
            + "</div>"
        )
    return (
        "<h2>Value watch</h2>"
        "<p class='meta'>Expert support at longer prices.</p>"
        f"<div class='cards'>{''.join(body)}</div>"
    )


def _longshot_section(race: Race) -> str:
    rows = longshot_watch(race)
    if not rows:
        return ""
    body = []
    for l in rows:
        first_note = (l.horse.notes.splitlines()[0] if l.horse.notes else "").strip()
        body.append(
            "<div class='card'>"
            f"<div><span class='post'>#{l.horse.post}</span>"
            f"<span class='name'>{_esc(l.horse.name)}</span> "
            f"<span class='ml'>{_esc(l.horse.ml)} &middot; {l.imp_pct:.1f}% imp</span></div>"
            + (f"<div class='note'>{_esc(first_note)}</div>" if first_note else "")
            + "</div>"
        )
    return (
        "<h2>Longshot watch</h2>"
        f"<div class='cards'>{''.join(body)}</div>"
    )


def _field_table(race: Race) -> str:
    head = (
        "<tr><th class='num'>Post</th><th>Horse</th><th>ML</th>"
        "<th class='num'>Imp%</th><th>Live</th><th class='num'>Overlay</th>"
        "<th>Style</th><th>Score</th><th>Experts</th></tr>"
    )
    body = []
    for h in race.horses:
        imp = implied_probability(h.ml) * 100
        ov = overlay_pct(h.ml, h.live_odds)
        ov_str = f"{ov:+.1f}%" if ov is not None else "—"
        live = h.live_odds or "—"
        score = race.support_score(h.post)
        body.append(
            f"<tr>"
            f"<td class='num'>{h.post}</td>"
            f"<td>{_esc(h.name)}</td>"
            f"<td>{_esc(h.ml)}</td>"
            f"<td class='num'>{imp:.1f}%</td>"
            f"<td>{_esc(live)}</td>"
            f"<td class='num'>{_esc(ov_str)}</td>"
            f"<td>{_esc(h.style)}</td>"
            f"<td class='num'>{score}</td>"
            f"<td>{_support_tags(race, h.post)}</td>"
            f"</tr>"
        )
    return f"<h2>Full field</h2><table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def _experts_section(race: Race) -> str:
    if not race.experts:
        return ""
    cards = []
    for e in race.experts:
        cards.append(_expert_card(race, e))
    return f"<h2>Experts</h2>{''.join(cards)}"


def _expert_card(race: Race, e: Expert) -> str:
    pending = "<span class='pending'>[picks pending]</span>" if e.tbd else ""
    parts = [f"<h3>{_esc(e.name)} <span class='ml'>{_esc(e.affiliation)}</span> {pending}</h3>"]

    def fmt(label: str, posts: list[int]) -> str:
        if not posts:
            return ""
        names = ", ".join(
            f"#{p} {_esc(race.by_post(p).name)}" for p in posts
        )
        return f"<div class='picks'><strong>{label}:</strong> {names}</div>"

    parts.append(fmt("Top", e.top_picks))
    parts.append(fmt("Use", e.use_horses))
    parts.append(fmt("Longshots", e.longshots))
    if e.notes:
        parts.append(f"<div class='notes'>{_esc(e.notes.strip())}</div>")
    if e.source:
        parts.append(
            f"<div class='notes'>Source: <a href='{_esc(e.source)}'>{_esc(e.source)}</a></div>"
        )
    return f"<div class='expert'>{''.join(parts)}</div>"


def _tickets_section(suggestions: list) -> str:
    if not suggestions:
        return ""
    rows = []
    total = 0.0
    for t in suggestions:
        total += t.cost
        rows.append(
            f"<tr><td>{_esc(t.label)}</td>"
            f"<td>{_esc(t.bet_type)}</td>"
            f"<td class='num'>{t.combinations}</td>"
            f"<td class='num'>${t.base:.2f}</td>"
            f"<td class='num'>${t.cost:.2f}</td></tr>"
        )
    rows.append(
        f"<tr><td colspan='4' style='text-align:right'><strong>Total</strong></td>"
        f"<td class='num'><strong>${total:.2f}</strong></td></tr>"
    )
    head = (
        "<tr><th>Ticket</th><th>Type</th><th class='num'>Combos</th>"
        "<th class='num'>Base</th><th class='num'>Cost</th></tr>"
    )
    return f"<h2>Suggested tickets</h2><table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def _layout(title: str, body: str, prefix: str = "") -> str:
    """Render the page chrome.

    `prefix` is the relative path prefix to the site root (e.g. "" for root
    pages, "../" for pages in a subdirectory like docs/oaks_day/index.html).
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<header class="site">
  <h1>2026 Kentucky Oaks &amp; Derby — Betting Analysis</h1>
  <p>Pace shape, expert consensus, value flags, and ticket structures.</p>
  <nav>
    <a href="{prefix}index.html">Overview</a>
    <a href="{prefix}oaks_day/">Oaks Day card</a>
    <a href="{prefix}oaks.html">Oaks preview</a>
    <a href="{prefix}derby_day/">Derby Day card</a>
    <a href="{prefix}derby.html">Derby preview</a>
  </nav>
</header>
{body}
<footer>Built {ts}. Data is hand-curated from public sources; verify against the official Churchill Downs board before betting.</footer>
</div>
</body>
</html>
"""


def render_race(race: Race, suggestions: list) -> str:
    body = (
        f"<h1>{_race_title(race)}</h1>"
        f"<p class='meta'>{_meta(race)}</p>"
        + _pace_section(race)
        + _consensus_section(race)
        + _value_section(race)
        + _longshot_section(race)
        + _tickets_section(suggestions)
        + _field_table(race)
        + _experts_section(race)
    )
    return _layout(race.name, body)


def _card_table(card: Card, marquee_link_prefix: str = "") -> str:
    """Render a card schedule as a single HTML table.

    `marquee_link_prefix` is prepended to the marquee race link target
    (e.g. "" when on the root index, "../" when on a subdir page).
    """
    rows = []
    for cr in card.races:
        purse = f"${cr.race.purse_usd:,}" if cr.race.purse_usd else "—"
        is_marquee = card.marquee is cr
        name_html = _esc(cr.race.name)
        if is_marquee:
            target = (
                f"{marquee_link_prefix}oaks.html"
                if "Oaks" in card.name
                else f"{marquee_link_prefix}derby.html"
            )
            name_html = f"<a href='{target}'>{name_html}</a>"
        status_tag = ""
        if cr.field_status == "skeleton":
            status_tag = " <span class='tag'>skeleton</span>"
        elif cr.field_status == "stakes-only":
            status_tag = " <span class='tag use'>stakes</span>"
        elif cr.field_status == "full":
            status_tag = " <span class='tag top'>full preview</span>"
        pick_html = (
            f"<strong>{_esc(cr.race.winner_pick)}</strong>"
            if cr.race.winner_pick
            else "<span class='ml'>—</span>"
        )
        rows.append(
            f"<tr>"
            f"<td class='num'>{cr.number}</td>"
            f"<td>{cr.race.post_time_et or '—'}</td>"
            f"<td>{name_html}{status_tag}</td>"
            f"<td>{_esc(cr.grade or '—')}</td>"
            f"<td>{_esc(cr.race.distance)}</td>"
            f"<td>{_esc(cr.surface or '—')}</td>"
            f"<td>{pick_html}</td>"
            f"<td class='num'>{purse}</td>"
            f"</tr>"
        )
    head = (
        "<tr><th class='num'>R#</th><th>Post</th><th>Race</th><th>Grade</th>"
        "<th>Distance</th><th>Surface</th><th>Pick</th><th class='num'>Purse</th></tr>"
    )
    return f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def render_index(races: list[tuple[str, Race]], cards: list[Card] | None = None) -> str:
    sections: list[str] = []

    if cards:
        # Inline the full schedule for each day so users can see all races
        # without clicking into a subpage.
        for c in cards:
            stakes_count = len(c.stakes)
            sections.append(
                f"<h2>{_esc(c.name)}</h2>"
                f"<p class='meta'>{_esc(c.date)} &middot; {_esc(c.track)} "
                f"&middot; {len(c.races)} races &middot; {stakes_count} graded/listed stakes</p>"
                f"{_card_table(c)}"
            )
            if c.notes:
                sections.append(f"<div class='proj'>{_esc(c.notes.strip())}</div>")

    # Marquee race summary cards (still useful as a quick jump).
    race_cards = []
    for slug, race in races:
        pending = [e.name for e in race.experts if e.tbd]
        pending_html = (
            f"<div class='note'>Pending: {_esc(', '.join(pending))}</div>"
            if pending else ""
        )
        race_cards.append(
            f"<a class='card' href='{_esc(slug)}.html' style='display:block;text-decoration:none;color:inherit'>"
            f"<div class='name'>{_esc(race.name)} &rarr; full preview</div>"
            f"<div class='ml'>{_meta(race)}</div>"
            f"{pending_html}"
            "</a>"
        )
    sections.append("<h2>Marquee race previews</h2>")
    sections.append(f"<div class='cards'>{''.join(race_cards)}</div>")

    sections += [
        "<h2>Tools</h2>",
        "<p>This site is generated from the same data the <code>kd</code> CLI uses. "
        "Run <code>kd preview oaks</code>, <code>kd preview derby</code>, or "
        "<code>kd card oaks_day</code> for a terminal view, or edit "
        "<code>data/&lt;day&gt;/*.yaml</code> to adjust running styles, expert picks, "
        "or live odds — the site rebuilds automatically on push to <code>main</code>.</p>",
    ]
    return _layout("2026 Kentucky Oaks & Derby", "".join(sections))


def _picks_section(card: Card) -> str:
    """Per-race winner picks with justification."""
    cards_html = []
    for cr in card.races:
        if not cr.race.winner_pick:
            continue
        cards_html.append(
            "<div class='card'>"
            f"<div><span class='post'>R{cr.number}</span>"
            f"<span class='ml'>{cr.race.post_time_et} ET &middot; {_esc(cr.race.name)}</span></div>"
            f"<div><strong>Pick: {_esc(cr.race.winner_pick)}</strong></div>"
            + (
                f"<div class='note'>{_esc(cr.race.winner_reason.strip())}</div>"
                if cr.race.winner_reason
                else ""
            )
            + "</div>"
        )
    if not cards_html:
        return ""
    return (
        "<h2>Winner picks</h2>"
        f"<div class='cards'>{''.join(cards_html)}</div>"
    )


def render_card(card: Card) -> str:
    """Render a per-day card index listing every race with details."""
    notes_html = (
        f"<div class='proj'>{_esc(card.notes.strip())}</div>"
        if card.notes else ""
    )
    body = (
        f"<h1>{_esc(card.name)}</h1>"
        f"<p class='meta'>{_esc(card.date)} &middot; {_esc(card.track)} &middot; {len(card.races)} races</p>"
        f"{_card_table(card, marquee_link_prefix='../')}"
        f"{notes_html}"
        f"{_picks_section(card)}"
    )
    return _layout(card.name, body, prefix="../")


def write_site(
    out_dir: Path,
    races: dict[str, Race],
    suggestions: dict[str, list],
    cards: dict[str, Card] | None = None,
) -> list[Path]:
    """Write index.html, marquee race pages, and per-day card pages."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug, race in races.items():
        path = out_dir / f"{slug}.html"
        path.write_text(render_race(race, suggestions.get(slug, [])))
        written.append(path)
    if cards:
        for slug, card in cards.items():
            day_dir = out_dir / slug
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "index.html").write_text(render_card(card))
            written.append(day_dir / "index.html")
    (out_dir / "index.html").write_text(
        render_index(
            [(slug, race) for slug, race in races.items()],
            cards=list(cards.values()) if cards else None,
        )
    )
    written.append(out_dir / "index.html")
    nojekyll = out_dir / ".nojekyll"
    nojekyll.write_text("")
    written.append(nojekyll)
    return written
