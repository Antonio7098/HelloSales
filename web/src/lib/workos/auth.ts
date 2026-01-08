/**
 * WorkOS authentication utilities for web.
 */

const WORKOS_ACCESS_TOKEN_KEY = 'hellosales_workos_access_token';
const WORKOS_REFRESH_TOKEN_KEY = 'hellosales_workos_refresh_token';
const WORKOS_CODE_VERIFIER_KEY = 'hellosales_workos_code_verifier';
const WORKOS_AUTH_STATE_KEY = 'hellosales_workos_auth_state';

const WORKOS_AUTH_URL = 'https://api.workos.com/user_management/authorize';

export interface WorkosTokenSet {
  accessToken: string;
  refreshToken: string | null;
}

/**
 * Generate random string (browser-compatible)
 */
function randomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  const randomValues = new Uint32Array(length);
  if (typeof window !== 'undefined' && window.crypto) {
    window.crypto.getRandomValues(randomValues);
  } else {
    for (let i = 0; i < length; i++) {
      randomValues[i] = Math.floor(Math.random() * 256);
    }
  }
  for (let i = 0; i < length; i++) {
    result += chars[randomValues[i] % chars.length];
  }
  return result;
}

/**
 * Generate PKCE code verifier and challenge
 */
export function generatePKCE(): { codeVerifier: string; codeChallenge: string } {
  const codeVerifier = randomString(64);

  // Use SubtleCrypto for SHA-256 (browser-compatible)
  async function sha256(str: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hash = await window.crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(hash)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  // This returns a promise but for the URL generation we need sync
  // So we'll handle it differently
  return { codeVerifier, codeChallenge: '' };
}

/**
 * Generate PKCE with async SHA-256 (for actual use)
 */
export async function generatePKCEAsync(): Promise<{ codeVerifier: string; codeChallenge: string }> {
  const codeVerifier = randomString(64);

  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const hash = await window.crypto.subtle.digest('SHA-256', data);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  return { codeVerifier, codeChallenge: base64 };
}

/**
 * Generate random state for CSRF protection
 */
export function generateState(): string {
  return randomString(32);
}

/**
 * Check if WorkOS is configured
 */
export function isWorkosConfigured(): boolean {
  if (typeof window !== 'undefined') {
    return !!(window as any).__ENV?.NEXT_PUBLIC_WORKOS_CLIENT_ID);
  }
  return !!process.env.NEXT_PUBLIC_WORKOS_CLIENT_ID;
}

/**
 * Get WorkOS client ID
 */
export function getWorkosClientId(): string | null {
  if (typeof window !== 'undefined') {
    return (window as any).__ENV?.NEXT_PUBLIC_WORKOS_CLIENT_ID || null;
  }
  return process.env.NEXT_PUBLIC_WORKOS_CLIENT_ID || null;
}

/**
 * Get WorkOS redirect URI
 */
export function getWorkosRedirectUri(): string {
  if (typeof window !== 'undefined') {
    return (window as any).__ENV?.NEXT_PUBLIC_WORKOS_REDIRECT_URI || `${window.location.origin}/auth/workos/callback`;
  }
  return process.env.NEXT_PUBLIC_WORKOS_REDIRECT_URI || '';
}

/**
 * Generate WorkOS authorization URL
 */
export async function getWorkosAuthorizationUrl(): Promise<string> {
  const clientId = getWorkosClientId();
  const redirectUri = getWorkosRedirectUri();
  const { codeVerifier, codeChallenge } = await generatePKCEAsync();
  const state = generateState();

  // Store code verifier and state for callback
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(WORKOS_CODE_VERIFIER_KEY, codeVerifier);
    sessionStorage.setItem(WORKOS_AUTH_STATE_KEY, state);
  }

  const params = new URLSearchParams({
    client_id: clientId || '',
    redirect_uri: redirectUri,
    response_type: 'code',
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    state,
  });

  return `${WORKOS_AUTH_URL}?${params.toString()}`;
}

/**
 * Load WorkOS tokens from storage
 */
export async function loadWorkosTokens(): Promise<WorkosTokenSet | null> {
  if (typeof window === 'undefined') return null;

  const accessToken = sessionStorage.getItem(WORKOS_ACCESS_TOKEN_KEY);
  if (!accessToken) return null;

  // Check if expired
  const payload = decodeJwtPayload(accessToken);
  const exp = payload?.exp;
  if (exp && Date.now() >= exp * 1000) {
    await clearWorkosTokens();
    return null;
  }

  const refreshToken = sessionStorage.getItem(WORKOS_REFRESH_TOKEN_KEY);
  return { accessToken, refreshToken };
}

/**
 * Save WorkOS tokens to storage
 */
export async function saveWorkosTokens(tokens: WorkosTokenSet): Promise<void> {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(WORKOS_ACCESS_TOKEN_KEY, tokens.accessToken);
  if (tokens.refreshToken) {
    sessionStorage.setItem(WORKOS_REFRESH_TOKEN_KEY, tokens.refreshToken);
  } else {
    sessionStorage.removeItem(WORKOS_REFRESH_TOKEN_KEY);
  }
}

/**
 * Clear WorkOS tokens from storage
 */
export async function clearWorkosTokens(): Promise<void> {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(WORKOS_ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(WORKOS_REFRESH_TOKEN_KEY);
}

/**
 * Load WorkOS auth session (code verifier and state)
 */
export async function loadWorkosAuthSession(): Promise<{
  codeVerifier: string | null;
  state: string | null;
}> {
  if (typeof window === 'undefined') {
    return { codeVerifier: null, state: null };
  }
  return {
    codeVerifier: sessionStorage.getItem(WORKOS_CODE_VERIFIER_KEY),
    state: sessionStorage.getItem(WORKOS_AUTH_STATE_KEY),
  };
}

/**
 * Clear WorkOS auth session
 */
export async function clearWorkosAuthSession(): Promise<void> {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(WORKOS_CODE_VERIFIER_KEY);
  sessionStorage.removeItem(WORKOS_AUTH_STATE_KEY);
}

/**
 * Exchange WorkOS authorization code for tokens
 */
export async function exchangeWorkosCode(code: string, codeVerifier: string): Promise<WorkosTokenSet> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const res = await fetch(`${apiUrl}/auth/workos/exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, code_verifier: codeVerifier }),
  });

  if (!res.ok) {
    throw new Error(`Token exchange failed: ${res.status}`);
  }

  const data = await res.json();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token ?? null,
  };
}

/**
 * Get valid access token
 */
export async function getAccessToken(): Promise<string | null> {
  const tokens = await loadWorkosTokens();
  if (!tokens) return null;
  return tokens.accessToken;
}

/**
 * Decode JWT payload (client-side)
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}
