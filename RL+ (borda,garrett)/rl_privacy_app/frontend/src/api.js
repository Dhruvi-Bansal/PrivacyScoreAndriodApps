async function request(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  categories: () => request("/api/categories"),
  permissions: () => request("/api/permissions"),
  examples: (key) => request(`/api/categories/${key}/examples`),
  analyze: (app) => request("/api/analyze", { method: "POST", body: JSON.stringify(app) }),
  analyzeUrl: (url, category) => request("/api/analyze-url", { method: "POST", body: JSON.stringify({ url, category }) }),
};

export const pct = (x, d = 1) => `${(100 * (x ?? 0)).toFixed(d)}%`;
