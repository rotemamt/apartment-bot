// Relative path: dev server proxies /api to the backend (see vite.config.js),
// and in production nginx does the same (see frontend/nginx.conf).
const API_BASE = "";

async function request(path, options = {}) {
  const tg = window.Telegram?.WebApp;
  const headers = { "Content-Type": "application/json", ...options.headers };
  // Raw signed initData (not initDataUnsafe) - the server verifies this
  // HMAC signature itself; the client never decides who it is.
  if (tg?.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  }
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!resp.ok) {
    const body = await resp.text();
    const err = new Error(`${resp.status} ${resp.statusText}: ${body}`);
    err.status = resp.status;
    throw err;
  }
  return resp.json();
}

export function getListings({ status, source, matchedOnly, sortBy, order } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (source) params.set("source", source);
  if (matchedOnly) params.set("matched_only", "true");
  if (sortBy) params.set("sort_by", sortBy);
  if (order) params.set("order", order);
  return request(`/api/listings?${params.toString()}`);
}

export function setListingStatus(id, status) {
  return request(`/api/listings/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function getStats() {
  return request("/api/stats");
}

export function getFilters() {
  return request("/api/filters");
}

export function getNeighborhoods() {
  return request("/api/neighborhoods");
}

export function updateFilters(filters) {
  return request("/api/filters", {
    method: "PUT",
    body: JSON.stringify(filters),
  });
}

export function getMe() {
  return request("/api/me");
}

export function postOnboarding(filters) {
  return request("/api/onboarding", {
    method: "POST",
    body: JSON.stringify(filters),
  });
}
