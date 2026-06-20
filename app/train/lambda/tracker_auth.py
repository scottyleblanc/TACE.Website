"""
tracker_auth.py -- Backend-for-Frontend (BFF) auth handler for the tracker.

Runs the OAuth2 Authorization Code + PKCE flow entirely server-side so the
refresh token is held only in an httpOnly, Secure, SameSite cookie that browser
JavaScript can never read. The SPA keeps a short-lived access token in memory
and re-mints it via /auth/refresh.

Routes (Lambda Function URL behind CloudFront /auth/*, payload format 2.0):
  GET  /auth/login    -- start login: set PKCE/state tx cookie, 302 to Cognito
  GET  /auth/callback -- exchange code for tokens, set refresh cookie, 302 to app
  POST /auth/refresh  -- mint a new access token from the refresh cookie
  GET  /auth/logout   -- clear the refresh cookie, 302 to Cognito logout

Environment:
  COGNITO_DOMAIN          Hosted UI base, e.g. https://<domain>.auth.<region>.amazoncognito.com
  CLIENT_ID               Cognito public app client id (no secret)
  REDIRECT_URI            https://train.tacedata.ca/auth/callback
  POST_LOGIN_REDIRECT     https://train.tacedata.ca/
  POST_LOGOUT_REDIRECT    https://train.tacedata.ca/
  SCOPES                  optional, defaults to "openid email profile"
  REFRESH_COOKIE_MAX_AGE  optional seconds, defaults to 2592000 (30 days)
  TX_COOKIE_MAX_AGE       optional seconds, defaults to 600 (10 minutes)

[SEC] No token, PKCE verifier, or OAuth state is ever returned to JS storage.
[SEC] Refresh token lives only in __Secure-trk_rt (HttpOnly; Secure; SameSite=Strict; Path=/auth).
[SEC] No token or authorization code is ever written to logs.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import urllib.parse
import urllib.request
from urllib.error import URLError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_COGNITO_DOMAIN = os.environ["COGNITO_DOMAIN"].rstrip("/")
_CLIENT_ID = os.environ["CLIENT_ID"]
_REDIRECT_URI = os.environ["REDIRECT_URI"]
_POST_LOGIN_REDIRECT = os.environ["POST_LOGIN_REDIRECT"]
_POST_LOGOUT_REDIRECT = os.environ.get("POST_LOGOUT_REDIRECT", _POST_LOGIN_REDIRECT)
_SCOPES = os.environ.get("SCOPES", "openid email profile")
_RT_MAX_AGE = int(os.environ.get("REFRESH_COOKIE_MAX_AGE", "2592000"))
_TX_MAX_AGE = int(os.environ.get("TX_COOKIE_MAX_AGE", "600"))

_RT_COOKIE = "__Secure-trk_rt"
_TX_COOKIE = "trk_tx"
_APP_ORIGIN = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(_POST_LOGIN_REDIRECT))


# --- encoding helpers --------------------------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _random_b64url(byte_count: int) -> str:
    return _b64url(secrets.token_bytes(byte_count))


def _pkce_challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


# --- cookie helpers ----------------------------------------------------------

def _request_cookies(event: dict) -> dict:
    out: dict = {}
    for raw in event.get("cookies", []) or []:
        name, sep, value = raw.partition("=")
        if sep:
            out[name.strip()] = value.strip()
    return out


def _set_cookie(name: str, value: str, max_age: int, same_site: str, path: str = "/auth") -> str:
    return f"{name}={value}; Max-Age={max_age}; Path={path}; HttpOnly; Secure; SameSite={same_site}"


def _clear_cookie(name: str, path: str = "/auth") -> str:
    return f"{name}=; Max-Age=0; Path={path}; HttpOnly; Secure; SameSite=Strict"


# --- response helpers --------------------------------------------------------

def _redirect(location: str, cookies: list[str] | None = None) -> dict:
    return {
        "statusCode": 302,
        "headers": {"Location": location, "Cache-Control": "no-store"},
        "cookies": cookies or [],
    }


def _json(status: int, body: dict, cookies: list[str] | None = None) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(body),
        "cookies": cookies or [],
    }


def _login_error(reason: str) -> dict:
    # Surface a coarse, non-sensitive reason to the SPA via a query param.
    target = f"{_POST_LOGIN_REDIRECT}?auth_error={urllib.parse.quote(reason)}"
    return _redirect(target, cookies=[_clear_cookie(_TX_COOKIE)])


# --- Cognito token endpoint --------------------------------------------------

def _token_request(params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode("ascii")
    req = urllib.request.Request(
        f"{_COGNITO_DOMAIN}/oauth2/token",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - fixed Cognito host
        return json.loads(resp.read().decode("utf-8"))


# --- route handlers ----------------------------------------------------------

def _handle_login() -> dict:
    verifier = _random_b64url(32)
    state = _random_b64url(16)
    challenge = _pkce_challenge(verifier)
    authorize = (
        f"{_COGNITO_DOMAIN}/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={urllib.parse.quote(_CLIENT_ID, safe='')}"
        f"&redirect_uri={urllib.parse.quote(_REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(_SCOPES)}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
        f"&state={state}"
    )
    tx = _set_cookie(_TX_COOKIE, f"{verifier}.{state}", _TX_MAX_AGE, same_site="Lax")
    logger.info("auth login: redirecting to Cognito authorize")
    return _redirect(authorize, cookies=[tx])


def _handle_callback(event: dict) -> dict:
    query = event.get("queryStringParameters") or {}
    if "error" in query:
        logger.info("auth callback: provider returned error")
        return _login_error(query.get("error", "provider_error"))

    code = query.get("code")
    state = query.get("state")
    tx = _request_cookies(event).get(_TX_COOKIE, "")
    if not code or "." not in tx:
        return _login_error("invalid_request")

    verifier, _, expected_state = tx.partition(".")
    if not state or not hmac.compare_digest(state, expected_state):
        logger.info("auth callback: state mismatch")
        return _login_error("state_mismatch")

    try:
        tokens = _token_request({
            "grant_type": "authorization_code",
            "client_id": _CLIENT_ID,
            "code": code,
            "redirect_uri": _REDIRECT_URI,
            "code_verifier": verifier,
        })
    except (URLError, ValueError):
        logger.info("auth callback: token exchange failed")
        return _login_error("exchange_failed")

    cookies = [_clear_cookie(_TX_COOKIE)]
    refresh = tokens.get("refresh_token")
    if refresh:
        cookies.append(_set_cookie(_RT_COOKIE, refresh, _RT_MAX_AGE, same_site="Strict"))
    logger.info("auth callback: session established")
    return _redirect(_POST_LOGIN_REDIRECT, cookies=cookies)


def _handle_refresh(event: dict) -> dict:
    if not _origin_ok(event):
        return _json(403, {"error": "forbidden"})

    refresh = _request_cookies(event).get(_RT_COOKIE)
    if not refresh:
        return _json(401, {"error": "no_session"})

    try:
        tokens = _token_request({
            "grant_type": "refresh_token",
            "client_id": _CLIENT_ID,
            "refresh_token": refresh,
        })
    except (URLError, ValueError):
        logger.info("auth refresh: refresh token rejected")
        return _json(401, {"error": "refresh_failed"}, cookies=[_clear_cookie(_RT_COOKIE)])

    body = {
        "access_token": tokens.get("access_token"),
        "id_token": tokens.get("id_token"),
        "expires_in": tokens.get("expires_in"),
        "token_type": tokens.get("token_type", "Bearer"),
    }
    # Honor refresh-token rotation if the pool has it enabled.
    cookies: list[str] = []
    rotated = tokens.get("refresh_token")
    if rotated and rotated != refresh:
        cookies.append(_set_cookie(_RT_COOKIE, rotated, _RT_MAX_AGE, same_site="Strict"))
    return _json(200, body, cookies=cookies)


def _handle_logout() -> dict:
    logout_url = (
        f"{_COGNITO_DOMAIN}/logout"
        f"?client_id={urllib.parse.quote(_CLIENT_ID, safe='')}"
        f"&logout_uri={urllib.parse.quote(_POST_LOGOUT_REDIRECT, safe='')}"
    )
    logger.info("auth logout: clearing session")
    return _redirect(logout_url, cookies=[_clear_cookie(_RT_COOKIE)])


def _origin_ok(event: dict) -> bool:
    # Defense in depth against CSRF on top of SameSite=Strict: if an Origin
    # header is present it must match the app origin. Absent Origin is allowed
    # (same-origin GETs/fetches may omit it); the Strict cookie still applies.
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    origin = headers.get("origin")
    return origin is None or origin == _APP_ORIGIN


def handler(event: dict, context) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    route = path.rstrip("/").rsplit("/", 1)[-1]
    logger.info("auth route=%s method=%s", route, method)

    if route == "login" and method == "GET":
        return _handle_login()
    if route == "callback" and method == "GET":
        return _handle_callback(event)
    if route == "refresh" and method == "POST":
        return _handle_refresh(event)
    if route == "logout" and method == "GET":
        return _handle_logout()
    return _json(404, {"error": "not_found"})
