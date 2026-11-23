"""Logout revokes the refresh token (SR-07). The wider O3 suite is still open."""

import logging
import urllib.parse
from urllib.error import HTTPError, URLError

import pytest

import tracker_auth

REFRESH = "test-refresh-token-value"


def _logout_event(cookie: str | None = REFRESH) -> dict:
    event = {"rawPath": "/auth/logout", "requestContext": {"http": {"method": "GET"}}}
    if cookie is not None:
        event["cookies"] = [f"__Secure-trk_rt={cookie}"]
    return event


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def urlopen(monkeypatch):
    """Record every urlopen call; set .error to make the call raise."""
    class Recorder:
        def __init__(self):
            self.requests = []
            self.error = None

        def __call__(self, req, timeout=None):
            self.requests.append(req)
            if self.error is not None:
                raise self.error
            return _Response()

    recorder = Recorder()
    monkeypatch.setattr(tracker_auth.urllib.request, "urlopen", recorder)
    return recorder


def _assert_signed_out(resp: dict) -> None:
    assert resp["statusCode"] == 302
    assert resp["headers"]["Location"].startswith("https://auth.example.test/logout?")
    assert resp["headers"]["Cache-Control"] == "no-store"
    assert any(c.startswith("__Secure-trk_rt=;") and "Max-Age=0" in c for c in resp["cookies"])


def test_logout_with_cookie_revokes_once(urlopen):
    resp = tracker_auth.handler(_logout_event(), None)

    _assert_signed_out(resp)
    assert len(urlopen.requests) == 1
    req = urlopen.requests[0]
    assert req.full_url == "https://auth.example.test/oauth2/revoke"
    assert req.get_method() == "POST"
    assert urllib.parse.parse_qs(req.data.decode("ascii")) == {
        "token": [REFRESH],
        "client_id": ["test-client-id"],
    }


def test_logout_without_cookie_does_not_call_cognito(urlopen):
    resp = tracker_auth.handler(_logout_event(cookie=None), None)

    _assert_signed_out(resp)
    assert urlopen.requests == []


@pytest.mark.parametrize("error", [
    URLError("unreachable"),
    HTTPError("https://auth.example.test/oauth2/revoke", 400, "Bad Request", {}, None),
    TimeoutError("timed out"),
], ids=["url-error", "http-error", "timeout"])
def test_revoke_failure_still_signs_out(urlopen, error):
    urlopen.error = error

    resp = tracker_auth.handler(_logout_event(), None)

    _assert_signed_out(resp)
    assert len(urlopen.requests) == 1


def test_revoke_failure_never_logs_the_token(urlopen, caplog):
    urlopen.error = URLError("unreachable")

    with caplog.at_level(logging.DEBUG):
        tracker_auth.handler(_logout_event(), None)

    assert "revocation failed" in caplog.text
    assert REFRESH not in caplog.text
