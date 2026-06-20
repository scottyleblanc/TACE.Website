"""
auth_guard.py -- Cognito Pre-Token-Generation trigger.

Rejects any login attempt where the email address is not in the
allowed set. Cognito calls this before issuing tokens, so an
unauthorised Google account never receives credentials.

Allowed emails are supplied via the ALLOWED_EMAILS Lambda environment
variable as a comma-separated list (e.g. "alice@example.com,bob@example.com").
"""

import os


def _allowed_emails() -> set[str]:
    raw = os.environ.get("ALLOWED_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def handler(event: dict, context) -> dict:
    email = event.get("request", {}).get("userAttributes", {}).get("email", "").lower()
    if email not in _allowed_emails():
        raise Exception(f"Access denied for {email}")
    return event
