"""The auth guard never puts a rejected email address in its error (SR-09, O6)."""

import pytest

import auth_guard


def _event(email: str) -> dict:
    return {"request": {"userAttributes": {"email": email}}}


def test_allowed_email_passes(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAILS", "owner@example.com")
    event = _event("Owner@Example.com")

    assert auth_guard.handler(event, None) is event


def test_rejected_email_is_not_in_the_error(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAILS", "owner@example.com")

    with pytest.raises(Exception) as excinfo:
        auth_guard.handler(_event("stranger@example.com"), None)

    assert str(excinfo.value) == "Access denied"
    assert "stranger" not in str(excinfo.value)
