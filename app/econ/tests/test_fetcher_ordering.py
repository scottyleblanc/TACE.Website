"""Order-independence — every fetcher must return identical output whatever order the
upstream API returns rows in. This is the bug class behind v3.3.1 (BoC Valet `recent=N`
is newest-first) and review finding R4 (bonds, Twelve Data, Yahoo relied on API order).
"""

import random
from datetime import datetime, timedelta, timezone

import pytest

import indicators

ORDERS = ["oldest_first", "newest_first", "shuffled"]


def arrange(rows, order):
    """rows are canonical oldest->newest."""
    if order == "oldest_first":
        return list(rows)
    if order == "newest_first":
        return list(reversed(rows))
    shuffled = list(rows)
    random.Random(20261111).shuffle(shuffled)
    return shuffled


def business_days(n, end=None):
    """n weekday dates ending at `end` (default: last weekday before today), oldest first."""
    day = end or datetime.now(timezone.utc).date() - timedelta(days=1)
    out = []
    while len(out) < n:
        if day.weekday() < 5:
            out.append(day.isoformat())
        day -= timedelta(days=1)
    return list(reversed(out))


# ── Canonical fixtures (oldest -> newest, strictly increasing values so order errors show)

BOC_ROWS   = [(d, "2.25" if i < 25 else "2.50") for i, d in enumerate(business_days(40))]
BOND_ROWS  = [(d, f"{3.00 + i / 100:.2f}", f"{3.40 + i / 100:.2f}") for i, d in enumerate(business_days(40))]
WTI_ROWS   = [(d, f"{60 + i / 2:.2f}") for i, d in enumerate(business_days(40))]
TD_ROWS    = [(d, f"{500 + i:.2f}") for i, d in enumerate(business_days(30))]
TSX_ROWS   = [(int(datetime.fromisoformat(d).replace(hour=14, tzinfo=timezone.utc).timestamp()), 25000.0 + i * 10)
              for i, d in enumerate(business_days(40))]
CPI_ROWS   = [(f"{2024 + (8 + i) // 12}-{(8 + i) % 12 + 1:02d}-01", f"{160 + i * 0.4:.1f}") for i in range(25)]


def serve_boc(http, order):
    http.route("V39079", lambda url: {"observations": [
        {"d": d, "V39079": {"v": v}} for d, v in arrange(BOC_ROWS, order)]})


def serve_bonds(http, order):
    http.route("bond_yields_benchmark", lambda url: {"observations": [
        {"d": d, "BD.CDN.5YR.DQ.YLD": {"v": b5}, "BD.CDN.10YR.DQ.YLD": {"v": b10}}
        for d, b5, b10 in arrange(BOND_ROWS, order)]})


def serve_wti(http, order):
    rows = arrange(WTI_ROWS + [("2026-01-01", ".")], order)  # FRED '.' = missing
    http.route("DCOILWTICO", lambda url: {"observations": [{"date": d, "value": v} for d, v in rows]})


def serve_td(http, order):
    http.route("/quote", lambda url: {"close": TD_ROWS[-1][1], "previous_close": TD_ROWS[-2][1]})
    http.route("/time_series", lambda url: {"values": [
        {"datetime": d, "close": c} for d, c in arrange(TD_ROWS, order)]})


def serve_tsx(http, order):
    rows = arrange(TSX_ROWS + [(TSX_ROWS[0][0] - 86400, None)], order)  # null close = halt
    http.route("GSPTSE", lambda url: {"chart": {"result": [{
        "timestamp": [t for t, _ in rows],
        "indicators": {"quote": [{"close": [c for _, c in rows]}]},
    }]}})


def serve_cpi(http, order):
    http.route("getDataFromVectorsAndLatestNPeriods", lambda url: [{"object": {"vectorDataPoint": [
        {"refPer": r, "value": v} for r, v in arrange(CPI_ROWS, order)]}}])


CASES = {
    "boc":   (serve_boc,   indicators.fetch_boc_rate),
    "bonds": (serve_bonds, indicators.fetch_bonds),
    "wti":   (serve_wti,   indicators.fetch_wti),
    "td":    (serve_td,    lambda: indicators.fetch_td_equity("SPY")),
    "tsx":   (serve_tsx,   indicators.fetch_tsx),
    "cpi":   (serve_cpi,   indicators.fetch_cpi),
}


def run_case(monkeypatch, name, order):
    """Run one fetcher against fixtures served in `order`. Builds a fresh router per call
    (the shared `http` fixture accumulates routes, and these tests call several orders)."""
    serve, fn = CASES[name]
    routes = []

    def dispatch(url):
        for needle, responder in routes:
            if needle in url:
                return responder(url)
        raise AssertionError(f"unrouted URL: {url}")

    class Router:
        def route(self, needle, responder):
            routes.append((needle, responder))

    monkeypatch.setattr(indicators, "http_get",  lambda url, timeout=15: dispatch(url))
    monkeypatch.setattr(indicators, "http_post", lambda url, body, timeout=15: dispatch(url))
    monkeypatch.setattr(indicators.time, "sleep", lambda s: None)
    serve(Router(), order)
    return fn()


@pytest.mark.parametrize("name", list(CASES))
def test_output_is_independent_of_api_order(monkeypatch, name):
    results = {order: run_case(monkeypatch, name, order) for order in ORDERS}
    assert results["newest_first"] == results["oldest_first"]
    assert results["shuffled"] == results["oldest_first"]


@pytest.mark.parametrize("name", list(CASES))
@pytest.mark.parametrize("order", ORDERS)
def test_current_value_is_the_newest_observation(monkeypatch, name, order):
    r = run_case(monkeypatch, name, order)
    if name == "boc":
        assert (r["cur"], r["prev"], r["date"]) == (2.50, 2.25, BOC_ROWS[25][0])
    elif name == "bonds":
        assert r["b5"]["cur"] == float(BOND_ROWS[-1][1])
        assert r["b5"]["prev"] == float(BOND_ROWS[-2][1])
        assert r["b10"]["cur"] == float(BOND_ROWS[-1][2])
        assert r["b5"]["date"] == BOND_ROWS[-1][0]
        assert r["b5"]["history"] == [float(b5) for _, b5, _ in BOND_ROWS[-30:]]
    elif name == "wti":
        assert (r["cur"], r["prev"], r["date"]) == (float(WTI_ROWS[-1][1]), float(WTI_ROWS[-2][1]), WTI_ROWS[-1][0])
        assert r["history"] == [float(v) for _, v in WTI_ROWS[-30:]]
    elif name == "td":
        assert r["history"] == [float(c) for _, c in TD_ROWS]
        assert r["history"][-1] == r["cur"]
    elif name == "tsx":
        assert (r["cur"], r["prev"]) == (TSX_ROWS[-1][1], TSX_ROWS[-2][1])
        assert r["history"] == [c for _, c in TSX_ROWS[-30:]]
    elif name == "cpi":
        cur, prev_m, prev_y = (float(CPI_ROWS[i][1]) for i in (-1, -2, -13))
        assert r["yoy"] == round((cur - prev_y) / prev_y * 100, 4)
        assert r["mom"] == round((cur - prev_m) / prev_m * 100, 4)
        assert r["ref_date"] == CPI_ROWS[-1][0][:7]
        assert len(r["yoy_history"]) == 13
        assert r["yoy_history"][-1] == r["yoy"]


def test_history_series_are_oldest_to_newest(monkeypatch):
    """Dashboard sparklines compare history[0] (oldest) with cur — history must ascend
    in time. Fixtures rise monotonically, so ascending time == ascending value."""
    for name in ("wti", "td", "tsx"):
        h = run_case(monkeypatch, name, "newest_first")["history"]
        assert h == sorted(h), name
    bonds = run_case(monkeypatch, "bonds", "newest_first")
    assert bonds["b5"]["history"] == sorted(bonds["b5"]["history"])
