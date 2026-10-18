// SmartDrive - API client, trace log and toast bus.

// One entry per data structure / algorithm. `hue` is a CSS variable, so dark mode follows automatically.
export const DS = {
  avl: { name: "AVL Tree", hue: "var(--avl)", cost: "O(log n)" },
  hash: { name: "Hash Table", hue: "var(--hash)", cost: "O(1) avg" },
  trie: { name: "Trie", hue: "var(--trie)", cost: "O(k)" },
  heap: { name: "Max Heap", hue: "var(--heap)", cost: "O(log n)" },
  merkle: { name: "Merkle Tree", hue: "var(--merkle)", cost: "O(log n) proof" },
  lcs: { name: "LCS Diff", hue: "var(--lcs)", cost: "O(m·n)" },
  knap: { name: "Knapsack", hue: "var(--knap)", cost: "DP O(n·W)" },
  edit: { name: "Edit Distance", hue: "var(--edit)", cost: "O(m·n)" },
  ai: { name: "TF-IDF AI", hue: "var(--ai)", cost: "inverted index" },
  disk: { name: "Storage", hue: "var(--muted)", cost: "disk I/O" },
};

const listeners = { trace: new Set(), toast: new Set(), change: new Set() };
const on = (kind) => (fn) => { listeners[kind].add(fn); return () => listeners[kind].delete(fn); };
export const onTrace = on("trace");
export const onToast = on("toast");
export const onFilesChanged = on("change"); // Fired after any upload/edit/delete so every page can refresh

export function trace(ds, text, ms) {
  const entry = { id: Math.random().toString(36).slice(2), ds, text, ms, at: new Date() };
  listeners.trace.forEach((fn) => fn(entry));
}
export function toast(text, bad = false) { listeners.toast.forEach((fn) => fn({ id: Math.random(), text, bad })); }
export function changed() { listeners.change.forEach((fn) => fn()); }

async function request(method, url, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
  }
  let res;
  try { res = await fetch(url, opts); }
  catch { throw new Error("Can't reach the SmartDrive server. Check that `python server.py` is running."); }
  const type = res.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    let msg = data?.detail ?? data;
    if (Array.isArray(msg)) msg = msg.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ");
    throw new Error(typeof msg === "string" ? msg : `Request failed (${res.status})`);
  }
  return data;
}

const q = (params) => {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && s.set(k, v));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const api = {
  stats: () => request("GET", "/api/stats"),
  files: (p = {}) => request("GET", `/api/files${q(p)}`),
  file: (id) => request("GET", `/api/files/${id}`),
  autocomplete: (text) => request("GET", `/api/autocomplete${q({ q: text })}`),
  search: (text) => request("GET", `/api/search${q({ q: text })}`),
  upload: (file, { priority = 5, description = "", tags = "" } = {}) => {
    const fd = new FormData();
    fd.append("file", file); fd.append("priority", priority);
    if (description) fd.append("description", description);
    if (tags) fd.append("tags", tags);
    return request("POST", "/api/files", fd, true);
  },
  createText: (body) => request("POST", "/api/files/text", body),
  uploadVersion: (id, file, description) => {
    const fd = new FormData();
    fd.append("file", file);
    if (description) fd.append("description", description);
    return request("PUT", `/api/files/${id}/content`, fd, true);
  },
  textVersion: (id, content, description) => request("PUT", `/api/files/${id}/text`, { content, description }),
  editMeta: (id, body) => request("PATCH", `/api/files/${id}`, body),
  remove: (id) => request("DELETE", `/api/files/${id}`),
  preview: (id, version) => request("GET", `/api/files/${id}/preview${q({ version })}`),
  downloadUrl: (id, version, inline) => `/api/files/${id}/download${q({ version, inline: inline ? "true" : undefined })}`,
  diff: (id, v1, v2) => request("GET", `/api/files/${id}/diff${q({ v1, v2 })}`),
  rollback: (id, version) => request("POST", `/api/files/${id}/rollback`, { version }),
  verify: (id) => request("GET", `/api/files/${id}/verify`),
  audit: () => request("GET", "/api/integrity/audit"),
  tamper: (id) => request("POST", `/api/files/${id}/tamper`),
  repair: (id) => request("POST", `/api/files/${id}/repair`),
  queue: () => request("GET", "/api/queue"),
  queueNext: () => request("POST", "/api/queue/next"),
  queueReset: () => request("POST", "/api/queue/reset"),
  optimize: (capacity_kb, method = "compare") => request("POST", "/api/optimize", { capacity_kb, method }),
  ask: (question) => request("POST", "/api/ai/ask", { question }),
  duplicates: () => request("GET", "/api/ai/duplicates"),
  insights: (id) => request("GET", `/api/files/${id}/insights`),
  applyAI: (id, body) => request("POST", `/api/files/${id}/ai/apply`, body),
  explorer: (structure, prefix) => request("GET", `/api/explorer/${structure}${q({ prefix })}`),
  sandbox: (structure, keys, capacity) => request("POST", `/api/explorer/sandbox/${structure}`, { keys, capacity }),
  lcs: (a, b, mode) => request("POST", "/api/explorer/lcs", { a, b, mode }),
  editDistance: (a, b) => request("POST", "/api/explorer/edit-distance", { a, b }),
  knapsack: (items, capacity) => request("POST", "/api/explorer/knapsack", { items, capacity }),
};

// --- Formatting helpers ---
export function fmtBytes(n) {
  if (n == null) return "";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0, v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return i === 0 ? `${v} B` : `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}
export function fmtMs(ms) {
  if (ms == null) return "";
  return ms < 1 ? `${Math.round(ms * 1000)} µs` : `${ms.toFixed(ms < 10 ? 2 : 0)} ms`;
}
export function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
export const short = (h, n = 10) => (h ? `${h.slice(0, n)}…` : "—");
