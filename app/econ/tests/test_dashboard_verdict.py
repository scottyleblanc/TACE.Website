"""Dashboard "Overall read" — every card must count toward the verdict, and each tag must
name the indicators behind it.

Regression origin (V1, 2026-11-14): renderEquity() returned the CSS class ('sig-wait'),
buildVerdict() counted 'wait', so S&P 500, TSX and crude oil never counted. The read
showed "1 counter-signal" when there were 2 (5yr yield and crude oil).

Runs the real inline dashboard script in Node with a stub DOM. Skipped if Node is absent
(GitHub's ubuntu-latest runners include it, so the CI gate runs it).
"""

import json
import os
import shutil
import subprocess

import pytest

from conftest import DASHBOARD_HTML

HARNESS = os.path.join(os.path.dirname(__file__), "dashboard_harness.js")
NODE    = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def series(start, end, n=30):
    return [round(start + (end - start) * i / (n - 1), 4) for i in range(n)]


def card(start, end):
    h = series(start, end)
    return {"cur": h[-1], "prev": h[-2], "history": h}


def bond(start, end):
    return {**card(start, end), "date": "2026-11-13", "stale": False}


def boc(outcome):
    before, after = {"hike": (2.25, 2.50), "cut": (2.75, 2.50), "hold": (2.50, 2.50)}[outcome]
    return {"cur": after, "prev": before, "date": "2026-10-29", "next_decision": "2026-12-09",
            "last_decision": {"date": "2026-10-28", "effective": "2026-10-29",
                              "outcome": outcome, "before": before, "after": after}}


def cpi(yoy):
    return {"yoy": yoy, "mom": 0.2, "yoy_history": series(2.5, yoy, 13), "ref_date": "2026-10"}


NEUTRAL = {
    "generated_at": "2026-11-14T15:00:00Z",
    "boc":   boc("hold"),
    "bonds": {"b5": bond(3.30, 3.30), "b10": bond(3.60, 3.60)},
    "cpi":   cpi(2.2),
    "sp":    card(600, 600),
    "tsx":   card(25000, 25000),
    "oil":   card(60, 60),
    "cad":   card(0.72, 0.72),
}


def render(tmp_path, **overrides):
    feed = {**NEUTRAL, **overrides}
    path = tmp_path / "feed.json"
    path.write_text(json.dumps(feed), encoding="utf-8")
    out = subprocess.run([NODE, HARNESS, DASHBOARD_HTML, str(path)],
                         capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(out.stdout)


def labels(result):
    return [t["label"] for t in result["tags"]]


def test_2026_11_14_read_counts_crude_oil(tmp_path):
    # The reported case: BoC hike + CPI > 3% lock; 5yr yield drifting down and oil falling
    # are both counter-signals. Before the fix oil was dropped -> "1 counter-signal".
    r = render(tmp_path, boc=boc("hike"), cpi=cpi(3.1),
               bonds={"b5": bond(3.55, 3.35), "b10": bond(3.63, 3.63)},
               oil=card(68, 60))
    assert labels(r) == ["2 lock signals: BoC rate · CPI",
                         "2 counter-signals: 5yr yield · Crude oil"]


def test_every_card_counts(tmp_path):
    r = render(tmp_path,
               boc=boc("hike"),                                         # lock
               bonds={"b5": bond(3.10, 3.50), "b10": bond(3.40, 3.30)},  # 5yr lock, 10yr inverted -> watch
               cpi=cpi(3.5),                                            # lock
               sp=card(510, 450),                                       # -11.8% -> wait
               tsx=card(25000, 24000),                                  # -4%    -> watch
               oil=card(60, 70),                                        # +16.7% -> lock
               cad=card(0.74, 0.71))                                    # -4%    -> watch
    assert labels(r) == ["4 lock signals: BoC rate · 5yr yield · CPI · Crude oil",
                         "1 counter-signal: S&P 500"]


def test_market_cards_alone_can_drive_the_verdict(tmp_path):
    # Old code: equity signals never counted, so this read "No dominant signal"
    r = render(tmp_path, sp=card(680, 600), tsx=card(28000, 24500), oil=card(68, 60))
    assert labels(r) == ["3 stay-variable signals: S&P 500 · TSX · Crude oil"]
    assert r["text"].startswith("Multiple signals suggest rates may ease")


def test_watch_signals_are_named(tmp_path):
    r = render(tmp_path, tsx=card(25000, 24000), cad=card(0.74, 0.71))
    assert labels(r) == ["2 watch signals: TSX · CAD/USD"]


def test_all_neutral(tmp_path):
    assert labels(render(tmp_path)) == ["No dominant signal"]


def test_failed_sections_count_as_neutral_and_do_not_break_names(tmp_path):
    r = render(tmp_path, boc=boc("hike"), cpi=None, oil=None, sp=card(510, 450), tsx=card(28000, 24500))
    assert labels(r) == ["2 stay-variable signals: S&P 500 · TSX", "1 lock signal: BoC rate"]
