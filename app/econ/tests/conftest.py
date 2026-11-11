import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

sys.path.insert(0, os.path.join(_REPO, "app", "econ", "lambda"))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

# indicators.py reads these at import time; offline tests never call the real services.
os.environ.setdefault("TD_API_KEY", "test-td-key")
os.environ.setdefault("FRED_API_KEY", "test-fred-key")
os.environ.setdefault("S3_BUCKET", "test-bucket")

import indicators  # noqa: E402

REPO_ROOT      = _REPO
DASHBOARD_HTML = os.path.join(_REPO, "hugo", "static", "projects", "econ", "interest-rate", "index.html")


@pytest.fixture
def http(monkeypatch):
    """Route indicators.http_get / http_post by URL substring.
    Usage: http.route("V39079", lambda url: {...}). Unrouted URLs fail the test."""
    class Router:
        def __init__(self):
            self.routes = []
            self.calls  = []

        def route(self, needle, responder):
            self.routes.append((needle, responder))

        def _dispatch(self, url):
            self.calls.append(url)
            for needle, responder in self.routes:
                if needle in url:
                    return responder(url)
            raise AssertionError(f"unrouted URL in test: {url}")

    router = Router()
    monkeypatch.setattr(indicators, "http_get",  lambda url, timeout=15: router._dispatch(url))
    monkeypatch.setattr(indicators, "http_post", lambda url, body, timeout=15: router._dispatch(url))
    monkeypatch.setattr(indicators.time, "sleep", lambda s: None)
    return router


class FakeTable:
    """In-memory stand-in for the econ DynamoDB table (put_item only — reads are
    routed through monkeypatched _get_alert_record / _get_7day_snapshot)."""
    def __init__(self):
        self.items = {}
        self.fail_put = False

    def put_item(self, Item):  # noqa: N803 — mirrors boto3
        if self.fail_put:
            raise RuntimeError("dynamodb unavailable")
        self.items[(Item["pk"], Item["ts"])] = dict(Item)


@pytest.fixture
def alert_env(monkeypatch):
    """Wire check_thresholds() to an in-memory table and captured SNS publishes.
    Set env.prior_1d / env.prior_7d to control the comparison snapshots."""
    import boto3

    class Env:
        table    = FakeTable()
        sent     = []
        prior_1d = None
        prior_7d = None
        publish_fails = False

        def run(self, payload, ts=None):
            # Dedup compares sent_at against the wall clock, as in production — so the
            # default timestamp must be "now", not a fixed date.
            from datetime import datetime, timezone
            ts = ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            indicators.check_thresholds(payload, ts)

        def record(self, trigger_id):
            return self.table.items.get(("ALERT", trigger_id))

        def subjects(self):
            return [s for s, _ in self.sent]

    env = Env()
    env.table, env.sent = FakeTable(), []

    class _Resource:
        def Table(self, name):  # noqa: N802
            return env.table

    def publish(subject, message):
        if env.publish_fails:
            raise RuntimeError("sns unavailable")
        env.sent.append((subject, message))

    # Keep the schedule ops alert quiet unless a test sets a short schedule itself,
    # so alert tests do not start failing as the real schedule nears its end.
    monkeypatch.setattr(indicators, "BOC_DECISION_DATES", ("2099-12-09",))
    monkeypatch.setattr(indicators, "SNS_TOPIC_ARN", "arn:test")
    monkeypatch.setattr(boto3, "resource", lambda *a, **k: _Resource())
    monkeypatch.setattr(indicators, "_publish_alert", publish)
    monkeypatch.setattr(indicators, "_get_alert_record", lambda table, tid: table.items.get(("ALERT", tid)))
    monkeypatch.setattr(indicators, "_get_7day_snapshot",
                        lambda table, days=7: env.prior_1d if days == 1 else env.prior_7d)
    return env
