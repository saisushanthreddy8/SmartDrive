import { useEffect, useState } from "react";
import { DS } from "./api.js";
import { Toasts, TraceStrip } from "./components/Common.jsx";
import { Logo } from "./components/Icons.jsx";
import AssistantPage from "./pages/AssistantPage.jsx";
import Drive from "./pages/Drive.jsx";
import ExplorerPage from "./pages/ExplorerPage.jsx";
import IntegrityPage from "./pages/IntegrityPage.jsx";
import OptimizerPage from "./pages/OptimizerPage.jsx";
import QueuePage from "./pages/QueuePage.jsx";
import SearchPage from "./pages/SearchPage.jsx";

// `uses` names the data structures behind each page (shown under the nav label)
const PAGES = [
  { id: "drive", label: "Drive", hue: "var(--chrome-ink)", uses: "AVL, hash table, trie" },
  { id: "search", label: "Search", hue: DS.trie.hue, uses: "Trie, edit distance, TF-IDF" },
  { id: "queue", label: "Priority queue", hue: DS.heap.hue, uses: "Max heap" },
  { id: "integrity", label: "Integrity", hue: DS.merkle.hue, uses: "Merkle tree, SHA-256" },
  { id: "optimizer", label: "Storage optimizer", hue: DS.knap.hue, uses: "Knapsack: DP, greedy, B&B" },
  { id: "explorer", label: "Algorithm explorer", hue: DS.avl.hue, uses: "Every structure, step by step" },
  { id: "assistant", label: "AI assistant", hue: DS.ai.hue, uses: "TF-IDF, inverted index" },
];

// Tiny hash router: #/page/arg?q=...
function parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [path, query = ""] = raw.split("?");
  const [page = "drive", arg = ""] = path.split("/");
  return { page: PAGES.some((p) => p.id === page) ? page : "drive", arg: decodeURIComponent(arg), params: new URLSearchParams(query) };
}

function useTheme() {
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem("sd-theme") || "auto"; } catch { return "auto"; } });
  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("sd-theme", theme); } catch { /* storage unavailable */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "auto" ? "dark" : t === "dark" ? "light" : "auto"))];
}

export default function App() {
  const [route, setRoute] = useState(parseHash);
  const [selected, setSelected] = useState(null);
  const [theme, cycleTheme] = useTheme();
  useEffect(() => {
    const fn = () => setRoute(parseHash());
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);
  const go = (hash) => { window.location.hash = hash; };
  const openFile = (id) => { setSelected(id); go("/drive"); };
  const goSearch = (q) => go(`/search?q=${encodeURIComponent(q)}`);

  const { page } = route;
  return (
    <div className="shell">
      <nav className="nav" aria-label="Main">
        <div className="brand"><Logo /> SmartDrive</div>
        {PAGES.map((p) => (
          <button key={p.id} className="nav-item" aria-current={page === p.id ? "page" : undefined} style={{ "--nav-hue": p.hue }} onClick={() => go(`/${p.id}`)}>
            <span className="swatch" /><span>{p.label}</span><span className="uses">{p.uses}</span>
          </button>
        ))}
        <div className="nav-foot">
          <span>Advanced DSA file manager. Phase 5.</span>
          <button className="theme-btn" onClick={cycleTheme}>Theme: {theme}</button>
          <a href="/docs" target="_blank" rel="noreferrer">API documentation</a>
        </div>
      </nav>
      <main className="main" id="main">
        {page === "drive" && <Drive selected={selected} setSelected={setSelected} goSearch={goSearch} />}
        {page === "search" && <SearchPage initial={route.params.get("q") || ""} openFile={openFile} />}
        {page === "queue" && <QueuePage openFile={openFile} />}
        {page === "integrity" && <IntegrityPage openFile={openFile} />}
        {page === "optimizer" && <OptimizerPage openFile={openFile} />}
        {page === "explorer" && <ExplorerPage initialTab={route.arg} />}
        {page === "assistant" && <AssistantPage openFile={openFile} />}
      </main>
      <TraceStrip />
      <Toasts />
    </div>
  );
}
