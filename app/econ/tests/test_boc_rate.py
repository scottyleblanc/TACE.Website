"""BoC overnight rate fetch, decision classification, and history correction.

Regression origin (v3.3.1): Valet returns `recent=N` observations newest-first and
date-range observations oldest-first. The Lambda assumed oldest-first for a
`recent=10` query and reported the 2026-10-28 hike to 2.50% as a cut to 2.25%.
Follow-up (v3.4.0): with `prev` meaning "rate before the last change", the dashboard
could never show HELD — the signal now comes from the last scheduled decision.
"""

from datetime import date

import pytest

import fix_boc_history as fix
import indicators


# Real Valet `recent=10` response shape from 2026-11-11 (newest-first)
NEWEST_FIRST = [
    ("2026-11-10", "2.50"), ("2026-11-09", "2.50"), ("2026-11-06", "2.50"),
    ("2026-11-05", "2.50"), ("2026-11-04", "2.50"), ("2026-11-03", "2.50"),
    ("2026-11-02", "2.50"), ("2026-10-30", "2.50"), ("2026-10-29", "2.50"),
    ("2026-10-28", "2.25"),
]


def valet(rows):
    return {"observations": [{"d": d, "V39079": {"v": v}} for d, v in rows]}


def obs(*rows):
    return [(d, float(r)) for d, r in rows]


class TestFetchBocRate:
    @pytest.fixture
    def serve(self, http):
        def install(rows):
            http.route("V39079", lambda url: valet(rows))
            return http.calls
        return install

    def test_newest_first_response_reports_hike(self, serve):
        serve(NEWEST_FIRST)
        r = indicators.fetch_boc_rate()
        assert (r["cur"], r["prev"], r["date"]) == (2.50, 2.25, "2026-10-29")

    def test_oldest_first_response_gives_same_result(self, serve):
        serve(list(reversed(NEWEST_FIRST)))
        r = indicators.fetch_boc_rate()
        assert (r["cur"], r["prev"], r["date"]) == (2.50, 2.25, "2026-10-29")

    def test_cut_is_reported_as_cut(self, serve):
        serve([("2026-06-01", "2.75"), ("2026-06-02", "2.75"), ("2026-06-03", "2.50")])
        r = indicators.fetch_boc_rate()
        assert (r["cur"], r["prev"], r["date"]) == (2.50, 2.75, "2026-06-03")

    def test_prev_is_rate_before_last_change_not_previous_day(self, serve):
        serve([("2026-01-05", "3.00"), ("2026-03-02", "2.75"),
               ("2026-03-03", "2.75"), ("2026-03-04", "2.75")])
        r = indicators.fetch_boc_rate()
        assert r["prev"] == 3.00 and r["date"] == "2026-03-02"

    def test_no_change_in_window_prev_equals_cur(self, serve):
        serve([("2026-01-05", "2.50"), ("2026-01-06", "2.50")])
        r = indicators.fetch_boc_rate()
        assert r["cur"] == r["prev"] == 2.50

    def test_blank_observations_are_skipped(self, serve):
        serve([("2026-11-10", "2.50"), ("2026-11-11", ""), ("2026-10-28", "2.25")])
        assert indicators.fetch_boc_rate()["cur"] == 2.50

    def test_uses_date_range_query_not_recent(self, serve):
        calls = serve(NEWEST_FIRST)
        indicators.fetch_boc_rate()
        assert "start_date=" in calls[0] and "recent=" not in calls[0]

    def test_payload_carries_decision_fields(self, serve):
        serve(NEWEST_FIRST)
        r = indicators.fetch_boc_rate()
        assert r["last_decision"]["date"] == "2026-10-28"
        assert r["last_decision"]["outcome"] == "hike"
        assert r["next_decision"] == "2026-12-09"


class TestDecisionSummary:
    SCHED = ("2026-09-02", "2026-10-28", "2026-12-09")

    def summary(self, rows, schedule=SCHED):
        return indicators.boc_decision_summary(obs(*rows), schedule)

    def test_hike(self):
        s = self.summary([("2026-10-27", "2.25"), ("2026-10-28", "2.25"), ("2026-10-29", "2.50")])
        assert s["last_decision"] == {"date": "2026-10-28", "effective": "2026-10-29",
                                      "outcome": "hike", "before": 2.25, "after": 2.50}
        assert s["next_decision"] == "2026-12-09"

    def test_cut(self):
        s = self.summary([("2026-10-28", "2.75"), ("2026-10-29", "2.50")])
        assert s["last_decision"]["outcome"] == "cut"

    def test_hold_after_hike_reads_hold(self):
        # The v3.3.1 regression: a hold must not inherit the previous hike's direction
        rows = [("2026-10-28", "2.25"), ("2026-10-29", "2.50"),
                ("2026-12-09", "2.50"), ("2026-12-10", "2.50")]
        s = self.summary(rows)
        assert s["last_decision"]["date"] == "2026-12-09"
        assert s["last_decision"]["outcome"] == "hold"
        assert s["next_decision"] is None

    def test_decision_day_before_effective_data_posts(self):
        # 2026-12-09 announced, but no 12-10 observation yet — still pending
        rows = [("2026-10-28", "2.25"), ("2026-10-29", "2.50"), ("2026-12-09", "2.50")]
        s = self.summary(rows)
        assert s["last_decision"]["date"] == "2026-10-28"
        assert s["next_decision"] == "2026-12-09"

    def test_effective_date_skips_weekend(self):
        s = self.summary([("2026-10-28", "2.25"), ("2026-11-02", "2.50")],
                         schedule=("2026-10-28",))
        assert s["last_decision"]["effective"] == "2026-11-02"

    def test_year_boundary(self):
        rows = [("2026-12-09", "2.50"), ("2026-12-10", "2.50"),
                ("2027-01-27", "2.50"), ("2027-01-28", "2.25")]
        s = self.summary(rows, schedule=("2026-12-09", "2027-01-27", "2027-03-03"))
        assert s["last_decision"]["date"] == "2027-01-27"
        assert s["last_decision"]["outcome"] == "cut"
        assert s["next_decision"] == "2027-03-03"

    def test_schedule_exhausted(self):
        s = self.summary([("2026-12-09", "2.50"), ("2026-12-10", "2.50")],
                         schedule=("2026-12-09",))
        assert s["last_decision"]["outcome"] == "hold"
        assert s["next_decision"] is None

    def test_decision_before_window_is_skipped(self):
        s = self.summary([("2026-10-29", "2.50"), ("2026-10-30", "2.50")],
                         schedule=("2026-01-28", "2026-12-09"))
        assert s["last_decision"] is None
        assert s["next_decision"] == "2026-12-09"


class TestSchedule:
    def test_dates_are_iso_sorted_unique(self):
        sched = indicators.BOC_DECISION_DATES
        assert list(sched) == sorted(set(sched))
        for d in sched:
            date.fromisoformat(d)

    def test_dates_are_wednesdays(self):
        # Every BoC fixed announcement date is a Wednesday. A typo that lands on another
        # Wednesday (2026-09-09 vs 2026-09-02) gets past this, hence test_known_2026_dates.
        for d in indicators.BOC_DECISION_DATES:
            assert date.fromisoformat(d).weekday() == 2, d

    def test_known_2026_dates(self):
        # Reconfirmed by the BoC 2027-schedule release (2026-07) — R12 regression
        sched = indicators.BOC_DECISION_DATES
        assert {"2026-09-02", "2026-10-28", "2026-12-09"} <= set(sched)
        assert "2026-09-09" not in sched


class TestHistoryCorrection:
    OBS = fix.parse_boc_observations(valet(NEWEST_FIRST))

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
