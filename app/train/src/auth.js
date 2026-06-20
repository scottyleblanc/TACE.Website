// Auth client for the server-side (BFF) OAuth flow.
//
// [SEC] No tokens, PKCE verifier, or OAuth state are ever stored in the browser.
// The refresh token lives only in an httpOnly cookie set by the /auth/* handler;
// the access token is held in memory for the lifetime of the page and re-minted
// from the refresh cookie via /auth/refresh on load and on expiry.

let _accessToken = null;
let _expiresAt = 0;

// Top-level navigations: the server handles the OAuth round trip end to end.
export function login() {
  window.location.href = '/auth/login';
}

export function logout() {
  _accessToken = null;
  _expiresAt = 0;
  // The handler clears the refresh cookie, then redirects through Cognito logout.
  window.location.href = '/auth/logout';
}

export function getAccessToken() {
  return _accessToken;
}

export function isTokenValid() {
  return !!_accessToken && Date.now() < _expiresAt - 60_000;
}

// Mint a fresh access token from the httpOnly refresh cookie. Returns true on
// success. On failure the in-memory token is cleared and the caller should
// fall back to login().
export async function refreshTokens() {
  let res;
  try {
    res = await fetch('/auth/refresh', { method: 'POST', credentials: 'same-origin' });
  } catch {
    return false;
  }
  if (!res.ok) {
    _accessToken = null;
    _expiresAt = 0;
    return false;
  }
  const data = await res.json();
  _accessToken = data.access_token || null;
  _expiresAt = Date.now() + (Number(data.expires_in) || 0) * 1000;
  return !!_accessToken;
}
