// Relative path: dev server proxies /api to the backend (see vite.config.js),
// and in production nginx does the same (see frontend/nginx.conf).
const API_BASE = "";

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${body}`);
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

export function getConfig() {
  return request("/api/config");
}

export function updateConfig(filters) {
  return request("/api/config", {
    method: "PUT",
    body: JSON.stringify(filters),
  });
}
