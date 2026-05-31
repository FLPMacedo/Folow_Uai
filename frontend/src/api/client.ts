// fetch wrapper centralizado.
// Base URL: localhost:8000/api (dev). Pra build prod, configurar via env.

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    message: string,
  ) {
    super(message);
  }
}

type Json = unknown;

async function request<T>(
  method: string,
  path: string,
  opts: { body?: Json; query?: Record<string, unknown>; raw?: boolean } = {},
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined || v === null || v === "") continue;
      url.searchParams.append(k, String(v));
    }
  }

  const init: RequestInit = {
    method,
    headers: opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
  };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);

  const r = await fetch(url, init);
  if (!r.ok) {
    // Lê stream UMA vez como texto, depois tenta parsear JSON.
    // Fetch consume o stream em qualquer .json()/.text(), não dá pra reler.
    const raw = await r.text();
    let body: unknown = raw;
    try { body = JSON.parse(raw); } catch { /* fica string */ }
    const msg = formatDetail(body) ?? r.statusText;
    throw new ApiError(r.status, body, `${method} ${path} → ${r.status}: ${msg}`);
  }
  if (opts.raw) return r as unknown as T;
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

/** Serializa Pydantic validation errors em algo lível. */
function formatDetail(body: unknown): string | null {
  if (body === null || body === undefined) return null;
  if (typeof body === "string") return body;
  if (typeof body !== "object") return String(body);
  const detail = (body as { detail?: unknown }).detail;
  if (detail === undefined) return JSON.stringify(body);
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // Pydantic: [{loc:["body","nome"], msg:"field required", type:"missing"}, ...]
    return detail.map((e) => {
      if (typeof e !== "object" || e === null) return String(e);
      const obj = e as { loc?: unknown[]; msg?: string; type?: string };
      const field = Array.isArray(obj.loc) ? obj.loc.slice(1).join(".") : "?";
      return `${field}: ${obj.msg ?? "erro"}`;
    }).join(" | ");
  }
  return JSON.stringify(detail);
}

export const api = {
  get:    <T>(path: string, query?: Record<string, unknown>) =>
    request<T>("GET", path, { query }),
  post:   <T>(path: string, body?: Json, query?: Record<string, unknown>) =>
    request<T>("POST", path, { body, query }),
  put:    <T>(path: string, body: Json) => request<T>("PUT", path, { body }),
  delete: (path: string) => request<void>("DELETE", path),
  raw:    (path: string, query?: Record<string, unknown>) =>
    request<Response>("GET", path, { query, raw: true }),
};
