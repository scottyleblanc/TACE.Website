"""Payload contract — a full handler() run with stubbed upstreams and AWS must produce
an indicators.json carrying every field the dashboard reads, and nothing sensitive.

DASHBOARD_FIELDS mirrors what hugo/static/projects/econ/interest-rate/index.html reads;
test_dashboard_still_reads_these_fields keeps the two sides linked.
"""

import json
import re

import pytest

import indicators
from conftest import DASHBOARD_HTML
from test_fetcher_ordering import serve_boc, serve_bonds, serve_cpi, serve_td, serve_tsx, serve_wti

DASHBOARD_FIELDS = {
    "boc":   ["cur", "prev", "date", "next_decision", "last_decision"],
    "bonds": ["b5", "b10"],
    "cpi":   ["yoy", "mom", "yoy_history", "ref_date"],
    "sp":    ["cur", "prev", "history"],
    "tsx":   ["cur", "prev", "history"],
    "oil":   ["cur", "prev", "history"],
    "cad":   ["cur", "prev", "history"],
}
BOND_FIELDS          = ["cur", "prev", "history", "date", "stale"]
LAST_DECISION_FIELDS = ["date", "effective", "outcome", "before", "after"]


@pytest.fixture
def run_handler(http, monkeypatch):
    written = {}
    monkeypatch.setattr(indicators, "write_to_s3", lambda payload, key=None, cache_control=None: written.update(payload))
    monkeypatch.setattr(indicators, "write_snapshot_to_dynamo", lambda payload, ts: None)
    monkeypatch.setattr(indicators, "check_thresholds", lambda payload, ts: None)
    monkeypatch.setattr(indicators, "generate_history_files", lambda ts: None)
    for serve in (serve_boc, serve_bonds, serve_cpi, serve_td, serve_tsx, serve_wti):
        serve(http, "newest_first")

    def run():
        result = indicators.handler({}, None)
        # Round-trip exactly as S3 would store it
        return result, json.loads(json.dumps(written))
    return run


def test_payload_has_every_field_the_dashboard_reads(run_handler):
    result, payload = run_handler()
    assert result == {"statusCode": 200, "errors": {}}
    assert "errors" not in payload
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", payload["generated_at"])
    for section, fields in DASHBOARD_FIELDS.items():
        assert payload[section] is not None, section
        for f in fields:
            assert f in payload[section], f"{section}.{f}"
    for b in ("b5", "b10"):
        for f in BOND_FIELDS:
            assert f in payload["bonds"][b], f"bonds.{b}.{f}"
    ld = payload["boc"]["last_decision"]
    if ld is not None:
        assert set(LAST_DECISION_FIELDS) <= set(ld)
        assert ld["outcome"] in ("hike", "cut", "hold")


def test_dashboard_still_reads_these_fields():
    html = open(DASHBOARD_HTML, encoding="utf-8").read()
    names = {f for fields in DASHBOARD_FIELDS.values() for f in fields}
    names |= set(BOND_FIELDS) | set(LAST_DECISION_FIELDS) | set(DASHBOARD_FIELDS) | {"generated_at", "errors"}
    missing = sorted(n for n in names if not re.search(rf"\.{n}\b", html))
    assert not missing, f"contract lists fields the dashboard no longer reads: {missing}"


def test_dashboard_has_no_hardcoded_schedule():
    # R2: one schedule, in the Lambda
    html = open(DASHBOARD_HTML, encoding="utf-8").read()
    assert not re.search(r"BOC_DATES|'20\d\d-\d\d-\d\d'\s*,\s*'20\d\d-\d\d-\d\d'", html)


def test_dashboard_notes_do_not_use_innerhtml():
    # R10: saved notes are user text
    html  = open(DASHBOARD_HTML, encoding="utf-8").read()
    notes = html[html.index("function renderNotes"):html.index("$('note-save-btn')")]
    assert "innerHTML" not in notes


class TestFetchErrorsArePublicSafe:
    """R6 [SEC] — indicators.json is public; upstream error text must not reach it."""

    SECRET = "apikey=test-fred-key&token=s3cr3t"

    def test_failed_source_gets_generic_message(self, run_handler, http, monkeypatch, capsys):
        def boom():
            raise RuntimeError(f"HTTP 401 for https://api.example/x?{self.SECRET}")
        monkeypatch.setattr(indicators, "fetch_wti", boom)
        result, payload = run_handler()

        assert payload["oil"] is None
        assert payload["errors"] == {"oil": indicators.PUBLIC_FETCH_ERROR}
        assert result["errors"] == {"oil": indicators.PUBLIC_FETCH_ERROR}
        assert self.SECRET not in json.dumps(payload)
        # Full detail still reaches CloudWatch for diagnosis
        assert self.SECRET in capsys.readouterr().out

    def test_twelve_data_error_body_not_published(self, run_handler, http):
        http.routes.insert(0, ("/quote", lambda url: {"status": "error", "message": f"bad key {self.SECRET}"}))
        _, payload = run_handler()
        assert payload["sp"] is None and payload["cad"] is None
        assert self.SECRET not in json.dumps(payload)

    def test_api_keys_never_in_payload(self, run_handler):
        _, payload = run_handler()
        blob = json.dumps(payload)
        assert indicators.TD_API_KEY not in blob
        assert indicators.FRED_API_KEY not in blob
