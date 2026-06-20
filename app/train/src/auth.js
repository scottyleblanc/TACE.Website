import { CLIENT_ID, AUTH_DOMAIN } from './config.js';

const REDIRECT_URI = 'https://train.tacedata.ca/';
const SCOPES = 'openid email profile';

// Token and OAuth transient state storage. sessionStorage is per-tab and clears on tab
// close, limiting token exposure and persistence if a script runs on the origin.
const store = window.sessionStorage;

function _randomBase64url(byteCount) {
  const arr = new Uint8Array(byteCount);
  crypto.getRandomValues(arr);
  return btoa(String.fromCharCode(...arr))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function _pkceChallenge(verifier) {
  const data = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export async function login() {
  const verifier  = _randomBase64url(32);
  const challenge = await _pkceChallenge(verifier);
  const state     = _randomBase64url(16);
  store.setItem('pkce_verifier', verifier);
  store.setItem('oauth_state', state);
  const url = `${AUTH_DOMAIN}/oauth2/authorize`
    + `?client_id=${CLIENT_ID}`
    + `&response_type=code`
    + `&scope=${encodeURIComponent(SCOPES)}`
    + `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`
    + `&code_challenge=${challenge}`
    + `&code_challenge_method=S256`
    + `&state=${state}`;
  window.location.href = url;
}

export async function handleCallback() {
  const params        = new URLSearchParams(window.location.search);
  const code          = params.get('code');
  const returnedState = params.get('state');
  const storedState   = store.getItem('oauth_state');
  const verifier      = store.getItem('pkce_verifier');

  if (!code || !verifier) return false;
  if (returnedState !== storedState) throw new Error('OAuth state mismatch');

  const body = new URLSearchParams({
    grant_type:    'authorization_code',
    client_id:     CLIENT_ID,
    code,
    redirect_uri:  REDIRECT_URI,
    code_verifier: verifier,
  });

  const res = await fetch(`${AUTH_DOMAIN}/oauth2/token`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${res.status}`);

  _storeTokens(await res.json());
  store.removeItem('pkce_verifier');
  store.removeItem('oauth_state');
  window.history.replaceState({}, '', '/');
  return true;
}

function _storeTokens(tokens) {
  store.setItem('access_token',  tokens.access_token);
  store.setItem('id_token',      tokens.id_token);
  store.setItem('refresh_token', tokens.refresh_token);
  store.setItem('token_expiry',  Date.now() + tokens.expires_in * 1000);
}

export function getAccessToken() {
  return store.getItem('access_token');
}

export function isTokenValid() {
  const token  = store.getItem('access_token');
  const expiry = parseInt(store.getItem('token_expiry') || '0', 10);
  return !!token && Date.now() < expiry - 60_000;
}

export async function refreshTokens() {
  const refreshToken = store.getItem('refresh_token');
  if (!refreshToken) return false;
  const body = new URLSearchParams({
    grant_type:    'refresh_token',
    client_id:     CLIENT_ID,
    refresh_token: refreshToken,
  });
  const res = await fetch(`${AUTH_DOMAIN}/oauth2/token`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!res.ok) return false;
  _storeTokens(await res.json());
  return true;
}

export function logout() {
  ['access_token', 'id_token', 'refresh_token', 'token_expiry', 'pkce_verifier', 'oauth_state']
    .forEach(k => store.removeItem(k));
  window.location.href = `${AUTH_DOMAIN}/logout`
    + `?client_id=${CLIENT_ID}`
    + `&logout_uri=${encodeURIComponent(REDIRECT_URI)}`;
}
