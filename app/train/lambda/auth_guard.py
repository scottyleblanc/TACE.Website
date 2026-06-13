"""
auth_guard.py -- Cognito Pre-Token-Generation trigger.

Rejects any login attempt where the email address is not in the
allowed set. Cognito calls this before issuing tokens, so an
unauthorised Google account never receives credentials.

Wired as: User Pool <COGNITO_USER_POOL_ID> -> Lambda triggers -> Pre-Token-Generation
"""

ALLOWED_EMAILS = {
    "<ALLOWED_EMAIL_1>",
    "<ALLOWED_EMAIL_2>",
}


def handler(event: dict, context) -> dict:
    email = event.get("request", {}).get("userAttributes", {}).get("email", "").lower()
    if email not in {e.lower() for e in ALLOWED_EMAILS}:
        raise Exception(f"Access denied for {email}")
    return event
