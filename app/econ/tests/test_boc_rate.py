"""Regression tests for the BoC overnight rate ordering bug (v3.2.2).

Valet returns `recent=N` observations newest-first and date-range observations
oldest-first. The Lambda previously assumed oldest-first for a `recent=10` query,
reporting a 2.25 -> 2.50 hike as a 2.50 -> 2.25 cut.
"""

import boto3
import pytest

import fix_boc_history as fix
import indicators


class _FakeDynamo:
    def Table(self, name):  # noqa: N802 — mirrors boto3 API
        return None


# Real Valet `recent=10` response shape from 2026-11-11 (newest-first)
NEWEST_FIRST = [
    ("2026-11-10", "2.50"), ("2026-11-09", "2.50"), ("2026-11-06", "2.50"),
    ("2026-11-05", "2.50"), ("2026-11-04", "2.50"), ("2026-11-03", "2.50"),
    ("2026-11-02", "2.50"), ("2026-10-30", "2.50"), ("2026-10-29", "2.50"),
    ("2026-10-28", "2.25"),
]


def _valet(rows):
    return {"observations": [{"d": d, "V39079": {"v": v}} for d, v in rows]}


@pytest.fixture
def stub_valet(monkeypatch):
    calls = []

    def install(rows):
        def fake_get(url, timeout=15):
            calls.append(url)
            return _valet(rows)
        monkeypatch.setattr(indicators, "http_get", fake_get)
        return calls
    return install


class TestFetchBocRate:
    def test_newest_first_response_reports_hike(self, stub_valet):
        stub_valet(NEWEST_FIRST)
        assert indicators.fetch_boc_rate() == {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"}

    def test_oldest_first_response_gives_same_result(self, stub_valet):
        stub_valet(list(reversed(NEWEST_FIRST)))
        assert indicators.fetch_boc_rate() == {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"}

    def test_cut_is_reported_as_cut(self, stub_valet):
        stub_valet([("2026-06-01", "2.75"), ("2026-06-02", "2.75"), ("2026-06-03", "2.50")])
        assert indicators.fetch_boc_rate() == {"cur": 2.50, "prev": 2.75, "date": "2026-06-03"}

    def test_prev_is_rate_before_last_change_not_previous_day(self, stub_valet):
        stub_valet([("2026-01-05", "3.00"), ("2026-03-02", "2.75"),
                    ("2026-03-03", "2.75"), ("2026-03-04", "2.75")])
        result = indicators.fetch_boc_rate()
        assert result["prev"] == 3.00
        assert result["date"] == "2026-03-02"

    def test_no_change_in_window_prev_equals_cur(self, stub_valet):
        stub_valet([("2026-01-05", "2.50"), ("2026-01-06", "2.50")])
        result = indicators.fetch_boc_rate()
        assert result["cur"] == result["prev"] == 2.50

    def test_blank_observations_are_skipped(self, stub_valet):
        stub_valet([("2026-11-10", "2.50"), ("2026-11-11", ""), ("2026-10-28", "2.25")])
        assert indicators.fetch_boc_rate()["cur"] == 2.50

    def test_uses_date_range_query_not_recent(self, stub_valet):
        calls = stub_valet(NEWEST_FIRST)
        indicators.fetch_boc_rate()
        assert "start_date=" in calls[0] and "recent=" not in calls[0]


class TestBocAlert:
    @pytest.fixture
    def alerts(self, monkeypatch):
        sent = []
        monkeypatch.setattr(indicators, "SNS_TOPIC_ARN", "arn:test")
        monkeypatch.setattr(boto3, "resource", lambda *a, **k: _FakeDynamo())
        monkeypatch.setattr(indicators, "_alert_sent_recently", lambda t, tid: False)
        monkeypatch.setattr(indicators, "_record_alert", lambda t, tid, ts: None)
        monkeypatch.setattr(indicators, "_publish_alert", lambda s, m: sent.append((s, m)))
        return sent

    def _run(self, monkeypatch, prior_boc, payload_boc):
        monkeypatch.setattr(indicators, "_get_7day_snapshot",
                            lambda table, days=7: {"boc": prior_boc} if days == 1 else None)
        indicators.check_thresholds({"boc": payload_boc}, "2026-10-29T15:00:00Z")

    def test_hike_since_prior_snapshot_alerts_raised(self, monkeypatch, alerts):
        self._run(monkeypatch, "2.25", {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"})
        assert len(alerts) == 1
        subject, message = alerts[0]
        assert "raised" in subject and "2.50%" in subject
        assert "Previous: 2.25%" in message
        assert "will increase" in message

    def test_cut_since_prior_snapshot_alerts_cut(self, monkeypatch, alerts):
        self._run(monkeypatch, "2.50", {"cur": 2.25, "prev": 2.50, "date": "2026-12-10"})
        assert len(alerts) == 1
        assert "cut" in alerts[0][0]
        assert "will decrease" in alerts[0][1]

    def test_no_alert_when_unchanged_since_prior_snapshot(self, monkeypatch, alerts):
        # payload prev differs from cur for weeks after a decision — must not re-alert
        self._run(monkeypatch, "2.5", {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"})
        assert alerts == []

    def test_no_alert_without_prior_snapshot(self, monkeypatch, alerts):
        monkeypatch.setattr(indicators, "_get_7day_snapshot", lambda table, days=7: None)
        indicators.check_thresholds({"boc": {"cur": 2.50, "prev": 2.25, "date": "x"}}, "ts")
        assert alerts == []


class TestHistoryCorrection:
    OBS = fix.parse_boc_observations(_valet(NEWEST_FIRST))

    def test_parse_sorts_oldest_first(self):
        assert self.OBS[0] == ("2026-10-28", 2.25)
        assert self.OBS[-1] == ("2026-11-10", 2.50)

    def test_rate_on_uses_latest_observation_on_or_before_day(self):
        assert fix.rate_on("2026-10-28", self.OBS) == 2.25
        assert fix.rate_on("2026-10-29", self.OBS) == 2.50
        assert fix.rate_on("2026-11-01", self.OBS) == 2.50  # weekend carries Friday's rate
        assert fix.rate_on("2026-10-27", self.OBS) is None

    def test_plan_flags_only_wrong_values(self):
        snapshots = [
            {"ts": "2026-10-28T20:00:00Z", "boc": "2.25"},  # correct
            {"ts": "2026-10-29T15:00:00Z", "boc": "2.25"},  # wrong — lagged
            {"ts": "2026-11-10T23:30:00Z", "boc": "2.25"},  # wrong — lagged
            {"ts": "2026-11-11T00:00:00Z", "boc": "2.5"},   # correct, different string form
            {"ts": "2026-11-11T00:30:00Z"},                 # boc fetch failed that run
            {"ts": "2026-10-01T12:00:00Z", "boc": "2.25"},  # before reference data
        ]
        corrections, stats = fix.plan_corrections(snapshots, self.OBS)
        assert [c["ts"] for c in corrections] == ["2026-10-29T15:00:00Z", "2026-11-10T23:30:00Z"]
        assert all(c["old"] == 2.25 and c["new"] == 2.50 for c in corrections)
        assert stats == {"checked": 5, "correct": 2, "wrong": 2, "missing_boc": 1, "no_reference": 1}
