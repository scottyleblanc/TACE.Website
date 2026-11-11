"""Alert behaviour across consecutive Lambda runs.

Crossing alerts (BoC change, CPI band crossings) must send exactly once per event.
Latched alerts (curve inversion, 7-day moves, schedule running out) must send once
when the condition starts, stay silent while it persists, and re-arm when it clears
(review finding R3). State is recorded before publishing (R7).
"""

import pytest

import indicators


def boc(cur):
    return {"cur": cur, "prev": cur, "date": "2026-10-29"}


def bonds(b5, b10):
    return {"b5": {"cur": b5}, "b10": {"cur": b10}}


# ── Crossing alerts ───────────────────────────────────────────────────────────

class TestBocChanged:
    def test_hike_alerts_raised(self, alert_env):
        alert_env.prior_1d = {"boc": "2.25"}
        alert_env.run({"boc": {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"}})
        assert len(alert_env.sent) == 1
        subject, message = alert_env.sent[0]
        assert "raised" in subject and "2.50%" in subject
        assert "Previous: 2.25%" in message and "will increase" in message

    def test_cut_alerts_cut(self, alert_env):
        alert_env.prior_1d = {"boc": "2.50"}
        alert_env.run({"boc": boc(2.25)})
        assert "cut" in alert_env.sent[0][0]
        assert "will decrease" in alert_env.sent[0][1]

    def test_unchanged_since_prior_snapshot_is_silent(self, alert_env):
        # payload prev differs from cur for weeks after a decision — must not alert
        alert_env.prior_1d = {"boc": "2.5"}
        alert_env.run({"boc": {"cur": 2.50, "prev": 2.25, "date": "2026-10-29"}})
        assert alert_env.sent == []

    def test_sends_once_across_the_24h_detection_window(self, alert_env):
        alert_env.prior_1d = {"boc": "2.25"}
        for _ in range(48):  # every 30-min run until the prior snapshot catches up
            alert_env.run({"boc": boc(2.50)})
        assert len(alert_env.sent) == 1

    def test_no_prior_snapshot_is_silent(self, alert_env):
        alert_env.run({"boc": boc(2.50)})
        assert alert_env.sent == []


class TestCpiCrossings:
    def test_cross_above_3_uses_two_decimals(self, alert_env):
        # R11: 3.04 used to read "now 3.0%" (seen 2026-08-17)
        alert_env.prior_1d = {"cpi_yoy": "2.95"}
        alert_env.run({"cpi": {"yoy": 3.04}})
        assert alert_env.subjects() == ["[econ-alert] CPI YoY crossed above 3.0% — now 3.04%"]
        assert "was 2.95%" in alert_env.sent[0][1]

    def test_cross_below_2(self, alert_env):
        alert_env.prior_1d = {"cpi_yoy": "2.10"}
        alert_env.run({"cpi": {"yoy": 1.96}})
        assert alert_env.subjects() == ["[econ-alert] CPI YoY crossed below 2.0% — now 1.96%"]

    @pytest.mark.parametrize("prev,cur", [("3.10", "3.20"), ("2.50", "2.60"), ("1.80", "1.70")])
    def test_no_crossing_is_silent(self, alert_env, prev, cur):
        alert_env.prior_1d = {"cpi_yoy": prev}
        alert_env.run({"cpi": {"yoy": float(cur)}})
        assert alert_env.sent == []


# ── Latched alerts ────────────────────────────────────────────────────────────

class TestLatchedAlerts:
    INVERTED, NORMAL = bonds(3.60, 3.40), bonds(3.35, 3.63)

    def test_inversion_sends_once_while_it_persists(self, alert_env):
        # A month of daily runs, with sent_at a month old by the end — beyond any dedup window
        for day in range(1, 31):
            alert_env.run({"bonds": self.INVERTED}, ts=f"2026-10-{day:02d}T12:00:00Z")
        assert alert_env.subjects() == ["[econ-alert] Yield curve inverted — 10yr < 5yr"]

    def test_inversion_rearms_after_clearing(self, alert_env):
        alert_env.run({"bonds": self.INVERTED})
        alert_env.run({"bonds": self.NORMAL})
        assert alert_env.record("b10_invert")["active"] is False
        alert_env.run({"bonds": self.INVERTED})
        assert len(alert_env.sent) == 2

    def test_normal_curve_never_alerts(self, alert_env):
        alert_env.run({"bonds": self.NORMAL})
        assert alert_env.sent == []
        assert alert_env.record("b10_invert") is None

    def test_b5_up_7d_latches(self, alert_env):
        alert_env.prior_7d = {"b5": "3.00"}
        for _ in range(5):
            alert_env.run({"bonds": bonds(3.35, 3.63)})
        assert alert_env.subjects() == ["[econ-alert] GoC 5yr yield up +0.35% over 7 days"]

    def test_sp_down_7d_latches_and_rearms(self, alert_env):
        alert_env.prior_7d = {"sp": "600"}
        alert_env.run({"sp": {"cur": 530.0}})
        alert_env.run({"sp": {"cur": 525.0}})
        assert len(alert_env.sent) == 1
        alert_env.run({"sp": {"cur": 590.0}})   # recovered — re-arm
        alert_env.run({"sp": {"cur": 520.0}})
        assert len(alert_env.sent) == 2

    def test_missing_data_neither_sends_nor_rearms(self, alert_env):
        alert_env.prior_7d = {"sp": "600"}
        alert_env.run({"sp": {"cur": 530.0}})
        alert_env.prior_7d = None                # comparison snapshot unavailable
        alert_env.run({"sp": {"cur": 590.0}})
        assert alert_env.record("sp_down_7d")["active"] is True

    def test_pre_v340_record_without_active_flag(self, alert_env):
        # Old dedup records carry only sent_at; inside 24 h they suppress, then expire
        alert_env.table.put_item(Item={"pk": "ALERT", "ts": "b10_invert", "sent_at": "2000-01-01T00:00:00Z"})
        alert_env.run({"bonds": self.INVERTED})
        assert len(alert_env.sent) == 1

    def test_schedule_low_alert(self, alert_env, monkeypatch):
        monkeypatch.setattr(indicators, "BOC_DECISION_DATES", ("2026-12-09",))
        alert_env.run({})
        alert_env.run({})
        assert alert_env.subjects() == ["[econ-ops] BoC decision schedule needs updating"]
        assert "2026-12-09" in alert_env.sent[0][1]


# ── Record-before-publish (R7) ────────────────────────────────────────────────

class TestAlertStateOrdering:
    def test_state_write_failure_sends_nothing(self, alert_env):
        # Old order (publish then record) re-sent every 30 min when the record failed
        alert_env.table.fail_put = True
        for _ in range(3):
            alert_env.run({"bonds": TestLatchedAlerts.INVERTED})
        assert alert_env.sent == []

    def test_publish_failure_restores_state_so_next_run_retries(self, alert_env):
        alert_env.publish_fails = True
        alert_env.run({"bonds": TestLatchedAlerts.INVERTED})
        assert alert_env.record("b10_invert")["active"] is False
        alert_env.publish_fails = False
        alert_env.run({"bonds": TestLatchedAlerts.INVERTED})
        assert len(alert_env.sent) == 1

    def test_publish_failure_restores_prior_crossing_record(self, alert_env):
        alert_env.prior_1d = {"boc": "2.25"}
        alert_env.publish_fails = True
        alert_env.run({"boc": boc(2.50)})
        assert not indicators._sent_recently(alert_env.record("boc_changed"))
        alert_env.publish_fails = False
        alert_env.run({"boc": boc(2.50)})
        assert len(alert_env.sent) == 1


def test_alerting_disabled_without_topic(monkeypatch, alert_env):
    monkeypatch.setattr(indicators, "SNS_TOPIC_ARN", "")
    alert_env.prior_1d = {"boc": "2.25"}
    alert_env.run({"boc": boc(2.50), "bonds": TestLatchedAlerts.INVERTED})
    assert alert_env.sent == [] and alert_env.table.items == {}
