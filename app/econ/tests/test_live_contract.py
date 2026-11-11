"""Live upstream contract tests — opt-in, hit real public APIs (no keys needed).

    python -m pytest app/econ -m live

These pin the upstream behaviours the Lambda depends on or defends against, so an
upstream change shows up here first. The Lambda sorts explicitly and does not rely on
any of these orderings — a failure here is a heads-up, not necessarily a bug.
"""

import json
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

import indicators

pytestmark = pytest.mark.live

TODAY = datetime.now(timezone.utc).date()
START = TODAY - timedelta(days=60)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "tacedata-contract-tests/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def dates(observations, key="d"):
    return [o[key] for o in observations]


def test_valet_recent_n_is_newest_first():
    # The v3.3.1 root cause. If this flips, nothing breaks — the Lambda no longer uses recent=N.
    d = dates(get(f"{indicators.BOC_BASE}/observations/V39079/json?recent=10")["observations"])
    assert d == sorted(d, reverse=True)


def test_valet_date_range_is_oldest_first():
    d = dates(get(f"{indicators.BOC_BASE}/observations/V39079/json?start_date={START}&end_date={TODAY}")["observations"])
    assert d == sorted(d)


def test_valet_bond_group_date_range_is_oldest_first():
    url = f"{indicators.BOC_BASE}/observations/group/bond_yields_benchmark/json?start_date={START}&end_date={TODAY}"
    d = dates(get(url)["observations"])
    assert d == sorted(d)


def test_yahoo_tsx_timestamps_ascend():
    r  = get(f"{indicators.YF_BASE}/%5EGSPTSE?interval=1d&range=1mo")["chart"]["result"][0]
    ts = r["timestamp"]
    assert ts == sorted(ts)


def test_real_boc_fetch_is_sane():
    r = indicators.fetch_boc_rate()
    assert 0 <= r["cur"] <= 10
    assert r["last_decision"] is not None, "no scheduled decision resolved in the last 2 years"
    assert r["last_decision"]["date"] in indicators.BOC_DECISION_DATES
    assert r["last_decision"]["after"] == r["cur"]


def test_real_bond_fetch_is_sane():
    r = indicators.fetch_bonds()
    assert r["b5"]["history"][-1] == r["b5"]["cur"]
    assert len(r["b5"]["history"]) >= 10
