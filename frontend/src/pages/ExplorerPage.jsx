import { useEffect, useState } from "react";
import { api, DS, short, trace } from "../api.js";
import { DSLabel, ErrorNote, useLive, PageUses } from "../components/Common.jsx";
import DPTable from "../components/DPTable.jsx";
import { Back, Next, Play } from "../components/Icons.jsx";
import { layoutBinary, layoutNary, TreeSvg } from "../components/Trees.jsx";
import { HeapDiagram } from "./QueuePage.jsx";
import { MerkleDiagram } from "./IntegrityPage.jsx";

const TABS = [
  { id: "avl", ds: "avl" }, { id: "hash", ds: "hash" }, { id: "trie", ds: "trie" }, { id: "heap", ds: "heap" },
  { id: "merkle", ds: "merkle" }, { id: "lcs", ds: "lcs" }, { id: "edit", ds: "edit" }, { id: "knap", ds: "knap" },
];

// --- Shared pieces ---
function StepPlayer({ steps, children }) {
  const [i, setI] = useState(steps.length - 1);
  const [playing, setPlaying] = useState(false);
  useEffect(() => { setI(steps.length - 1); setPlaying(false); }, [steps]);
  useEffect(() => {
    if (!playing) return;
    if (i >= steps.length - 1) { setPlaying(false); return; }
    const t = setTimeout(() => setI((x) => x + 1), 900);
    return () => clearTimeout(t);
  }, [playing, i, steps.length]);
  if (!steps.length) return <div className="empty">Add some keys and press Run.</div>;
  const step = steps[Math.max(0, Math.min(i, steps.length - 1))];
  return (
    <div className="stack">
      <div className="steps">
        <button className="btn small" onClick={() => setI(Math.max(0, i - 1))} disabled={i <= 0} aria-label="Previous step"><Back /></button>
        <button className="btn small" onClick={() => { if (i >= steps.length - 1) setI(0); setPlaying(true); }} disabled={playing}><Play /> Replay</button>
        <button className="btn small" onClick={() => setI(Math.min(steps.length - 1, i + 1))} disabled={i >= steps.length - 1} aria-label="Next step"><Next /></button>
        <input type="range" min={0} max={steps.length - 1} value={i} onChange={(e) => { setPlaying(false); setI(Number(e.target.value)); }} aria-label="Step" style={{ flex: 1, minWidth: 120 }} />
        <span className="muted mono">step {i + 1}/{steps.length}</span>
      </div>
      <div className="step-op">{step.op}</div>
      {children(step, i)}
    </div>
  );
}

function KeysForm({ value, onChange: set, onRun, hint, extra }) {
  return (
    <form className="stack" style={{ gap: 6 }} onSubmit={(e) => { e.preventDefault(); onRun(); }}>
      <div className="row">
        <input className="input grow" value={value} onChange={(e) => set(e.target.value)} aria-label="Keys, comma separated" />
        {extra}
        <button className="btn primary">Run</button>
      </div>
      <span className="muted" style={{ fontSize: "0.82rem" }}>{hint}</span>
    </form>
  );
}

function ModeSwitch({ mode, setMode, live = "Your files", sandbox = "Sandbox" }) {
  return (
    <div className="chips" role="group" aria-label="Data source">
      <button className="chip" aria-pressed={mode === "live"} onClick={() => setMode("live")}>{live}</button>
      <button className="chip" aria-pressed={mode === "sandbox"} onClick={() => setMode("sandbox")}>{sandbox}</button>
    </div>
  );
}

const keysOf = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

// --- AVL ---
function AVLView({ root, hotKey }) {
  return (
    <TreeSvg layout={layoutBinary(root)} hue={DS.avl.hue} colW={root && String(root.key).length > 4 ? 60 : 44} rowH={66} pad={44} label="AVL tree"
      node={(n, x, y) => {
        const hot = String(n.data.key) === String(hotKey);
        const unbalanced = Math.abs(n.data.balance) > 1;
        return (
          <>
            <circle className={`node ${hot ? "hot" : ""} ${unbalanced ? "bad" : ""}`} cx={x} cy={y} r={16} />
            <text x={x} y={y + 4} textAnchor="middle" className={hot ? "on-hot" : ""}>{n.data.key.slice(0, 4)}</text>
            {n.data.key.length > 4 && <text x={x} y={y + 30} textAnchor="middle" className="small">{n.data.key.slice(0, 14)}</text>}
            <text x={x + 19} y={y - 12} className="small">h{n.data.height} b{n.data.balance > 0 ? "+" : ""}{n.data.balance}</text>
          </>
        );
      }} />
  );
}

function AVLTab() {
  const [mode, setMode] = useState("sandbox");
  const [keys, setKeys] = useState("10, 20, 30, 25, 28, 5, 4, 27, -20");
  const [steps, setSteps] = useState([]);
  const live = useLive(() => api.explorer("avl"));
  const run = async () => {
    const r = await api.sandbox("avl", keysOf(keys));
    setSteps(r.steps);
    const rot = r.steps.flatMap((s) => s.rotations);
    trace("avl", `${r.steps.length} operations, ${rot.length} rotation${rot.length === 1 ? "" : "s"}${rot.length ? ": " + rot.join(", ") : ""}`);
  };
  useEffect(() => { run(); }, []);
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="muted" style={{ maxWidth: "70ch" }}>A binary search tree that keeps every node’s left and right heights within 1. When an insert or delete breaks that, it rotates (LL, RR, LR or RL), so search stays O(log n).</p>
        <ModeSwitch mode={mode} setMode={setMode} />
      </div>
      {mode === "live" ? (
        live.data?.root ? <><span className="muted">Indexed by filename. {live.data.size} files, height {live.data.root.height}.</span><AVLView root={live.data.root} /></> : <div className="empty">No files indexed.</div>
      ) : (
        <>
          <KeysForm value={keys} onChange={setKeys} onRun={run} hint="Comma-separated keys are inserted in order. Prefix a key with - to delete it. Numbers are compared as numbers." />
          <StepPlayer steps={steps}>
            {(s) => (
              <>
                {s.rotations.length > 0
                  ? <div className="note" style={{ borderColor: "var(--avl)" }}>Rebalanced: {s.rotations.join(", ")} rotation. Height is now {s.height}.</div>
                  : <div className="muted" style={{ fontSize: "0.88rem" }}>No rotation needed. Height {s.height}.</div>}
                {s.root ? <AVLView root={s.root} hotKey={s.op.split(" ")[0] === "insert" ? s.op.split(" ")[1] : null} /> : <div className="empty">Tree is empty.</div>}
              </>
            )}
          </StepPlayer>
        </>
      )}
    </div>
  );
}

// --- Hash table ---
function Buckets({ data, hotKey, hotBucket }) {
  return (
    <div className="diagram panel-pad" style={{ "--hue": DS.hash.hue }}>
      <div className="buckets">
        {data.buckets.map((chain, i) => (
          <div className="bucket" key={i}>
            <span className="idx">[{i}]</span>
            <span className={`slot ${chain.length ? "full" : ""}`} style={i === hotBucket ? { outline: "2px solid var(--hash)", outlineOffset: 2 } : null} />
            {chain.map((k, j) => (
              <span key={j} className="row" style={{ gap: 6, flexWrap: "nowrap" }}>
                <span className="arrow">→</span><span className={`link ${k === hotKey ? "hot" : ""}`}>{k.length > 26 ? k.slice(0, 24) + "…" : k}</span>
              </span>
            ))}
            {chain.length > 0 && <span className="arrow muted">→ null</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function HashTab() {
  const [mode, setMode] = useState("sandbox");
  const [keys, setKeys] = useState("apple, banana, cherry, date, fig, grape, kiwi");
  const [cap, setCap] = useState(4);
  const [steps, setSteps] = useState([]);
  const live = useLive(() => api.explorer("hash"));
  const run = async () => {
    const r = await api.sandbox("hash", keysOf(keys), Number(cap));
    setSteps(r.steps);
    const last = r.steps[r.steps.length - 1];
    if (last) trace("hash", `${r.steps.length} inserts, capacity ${cap} -> ${last.capacity}, ${last.stats.total_collisions} collisions`);
  };
  useEffect(() => { run(); }, []);
  const Stats = ({ d }) => <span className="muted" style={{ fontSize: "0.86rem" }}>{d.size} keys in {d.capacity} buckets, load factor {d.load_factor} (resizes above {d.max_load_factor}), {d.stats.total_collisions} collisions, longest chain {d.stats.max_chain_length}</span>;
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="muted" style={{ maxWidth: "70ch" }}>A polynomial rolling hash picks a bucket for each key. Keys that land in the same bucket are chained in a linked list. When the table gets 75% full, it doubles and rehashes every key.</p>
        <ModeSwitch mode={mode} setMode={setMode} />
      </div>
      {mode === "live" ? (live.data && <><Stats d={live.data} /><Buckets data={live.data} /></>) : (
        <>
          <KeysForm value={keys} onChange={setKeys} onRun={run} hint="Keys are inserted in order. Start small to watch collisions and a resize."
            extra={<label className="row muted" style={{ gap: 6 }}>Start capacity<input className="input" type="number" min={1} max={64} value={cap} onChange={(e) => setCap(e.target.value)} style={{ width: 70 }} /></label>} />
          <StepPlayer steps={steps}>
            {(s) => (
              <>
                {s.note ? <div className="note" style={{ borderColor: "var(--hash)" }}>{s.note}</div> : <span className="muted" style={{ fontSize: "0.88rem" }}>Hashed to bucket {s.bucket}.</span>}
                <Stats d={s} />
                <Buckets data={s} hotKey={s.op.replace("insert ", "")} hotBucket={s.bucket} />
              </>
            )}
          </StepPlayer>
        </>
      )}
    </div>
  );
}

// --- Trie ---
function TrieView({ root, hotWord }) {
  const hot = (hotWord || "").toLowerCase();
  return (
    <TreeSvg layout={layoutNary(root)} hue={DS.trie.hue} colW={30} rowH={44} label="Trie"
      hotEdge={(a, b) => onPath(b)}
      node={(n, x, y) => {
        const d = n.data, isHot = onPath(n);
        return (
          <>
            <circle className={`node ${d.end ? "end" : ""} ${isHot ? "hot" : ""}`} cx={x} cy={y} r={n.depth === 0 ? 13 : 10} />
            <text x={x} y={y + 4} textAnchor="middle" className={isHot ? "on-hot" : ""}>{n.depth === 0 ? "·" : d.char}</text>
            {d.truncated && <text x={x + 12} y={y + 4} className="small">…</text>}
          </>
        );
      }} />
  );
  function onPath(n) { return Boolean(hot) && hot.startsWith(n.data.prefix); }
}

// Attach each node's full prefix so the path of a word can be highlighted.
function withPrefixes(root, base = "") {
  const walk = (n, p) => ({ ...n, prefix: p, children: n.children.map((c) => walk(c, p + c.char)) });
  return root ? walk(root, base) : root;
}

function TrieTab() {
  const [mode, setMode] = useState("sandbox");
  const [words, setWords] = useState("car, cart, care, cat, dog, dot");
  const [prefix, setPrefix] = useState("");
  const [steps, setSteps] = useState([]);
  const live = useLive(() => api.explorer("trie", prefix), [prefix]);
  const run = async () => {
    const r = await api.sandbox("trie", keysOf(words));
    setSteps(r.steps);
    const last = r.steps[r.steps.length - 1];
    if (last) trace("trie", `${last.words} words share ${last.nodes} nodes`);
  };
  useEffect(() => { run(); }, []);
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="muted" style={{ maxWidth: "70ch" }}>Each edge is one character, so words with the same start share a path. Finding every name that starts with a prefix costs O(k) for the prefix plus the matches. Filled nodes end a word.</p>
        <ModeSwitch mode={mode} setMode={setMode} />
      </div>
      {mode === "live" ? (
        <>
          <label className="row muted">Show the branch under<input className="input" value={prefix} onChange={(e) => setPrefix(e.target.value)} placeholder="e.g. ma" style={{ width: 160 }} /></label>
          {live.data?.root ? <TrieView root={withPrefixes(live.data.root, prefix.toLowerCase())} /> : <div className="empty">No filename starts with “{prefix}”.</div>}
        </>
      ) : (
        <>
          <KeysForm value={words} onChange={setWords} onRun={run} hint="Words are inserted in order. The highlighted path is the word just inserted." />
          <StepPlayer steps={steps}>
            {(s) => (
              <>
                <span className="muted" style={{ fontSize: "0.88rem" }}>{s.words} words stored in {s.nodes} nodes (including the root).</span>
                <TrieView root={withPrefixes(s.root, "")} hotWord={s.op.replace("insert ", "")} />
              </>
            )}
          </StepPlayer>
        </>
      )}
    </div>
  );
}

// --- Heap ---
function HeapTab() {
  const [ops, setOps] = useState("40, 10, 30, 50, 20, pop, 35, pop");
  const [steps, setSteps] = useState([]);
  const run = async () => {
    const r = await api.sandbox("heap", keysOf(ops));
    setSteps(r.steps);
    trace("heap", `${r.steps.length} heap operations replayed`);
  };
  useEffect(() => { run(); }, []);
  return (
    <div className="stack">
      <p className="muted" style={{ maxWidth: "70ch" }}>A complete binary tree stored in an array. Insert adds at the end and sifts up; extract-max moves the last item to the root and sifts down. Both are O(log n). The Priority queue page shows the heap built from your files.</p>
      <KeysForm value={ops} onChange={setOps} onRun={run} hint="Numbers are inserted as priorities. Write pop to extract the maximum." />
      <StepPlayer steps={steps}>
        {(s) => s.nodes.length ? (
          <>
            <HeapDiagram nodes={s.nodes} labelOf={(n) => n.label} />
            <div className="chips mono">{s.nodes.map((n) => <span key={n.index} className="tag">[{n.index}] {n.priority}</span>)}</div>
          </>
        ) : <div className="empty">Heap is empty.</div>}
      </StepPlayer>
    </div>
  );
}

// --- Merkle ---
function MerkleTab() {
  const tree = useLive(() => api.explorer("merkle"));
  const files = useLive(() => api.files());
  const [fid, setFid] = useState("");
  const [proof, setProof] = useState(null);
  const show = async (id) => {
    setFid(id);
    if (!id) { setProof(null); return; }
    const v = await api.verify(id);
    setProof(v);
    trace("merkle", `audit path for "${v.filename}": ${v.proof.length} sibling hashes`);
  };
  const hot = new Set(proof ? [proof.disk_hash, ...proof.proof.map((s) => s.result)] : []);
  return (
    <div className="stack">
      <p className="muted" style={{ maxWidth: "70ch" }}>Pick a file to see its audit proof. Only the sibling hash at each level is needed to recompute the root, so a proof has about log₂(n) steps.</p>
      <label className="row muted">Audit path for
        <select className="input" value={fid} onChange={(e) => show(e.target.value)}>
          <option value="">Choose a file</option>
          {(files.data?.files || []).map((f) => <option key={f.file_id} value={f.file_id}>{f.filename}</option>)}
        </select>
      </label>
      {proof && <div className={`note ${proof.valid ? "ok" : "bad"}`}>{proof.message} Path: {proof.proof.length} steps to root <span className="mono">{short(proof.root, 12)}</span>.</div>}
      {tree.data?.root ? <MerkleDiagram root={tree.data.root} hotPath={hot} bad={proof && !proof.valid ? new Set([proof.file_id]) : new Set()} /> : <div className="empty">No files yet.</div>}
    </div>
  );
}

// --- LCS ---
function LCSTab() {
  const [a, setA] = useState("ABCBDAB");
  const [b, setB] = useState("BDCABA");
  const [mode, setMode] = useState("chars");
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const run = async () => {
    setErr(null);
    try { const r = await api.lcs(a, b, mode); setRes(r); trace("lcs", `${r.a.length + 1}×${r.b.length + 1} table, LCS length ${r.length}`); }
    catch (e) { setErr(e); }
  };
  useEffect(() => { run(); }, []);
  const pathSet = new Set((res?.path || []).map(([i, j]) => `${i},${j}`));
  return (
    <div className="stack">
      <p className="muted" style={{ maxWidth: "70ch" }}>dp[i][j] is the longest common subsequence of the first i items of A and the first j items of B. Matching items extend the diagonal; otherwise take the larger of up and left. SmartDrive runs this on lines to diff file versions.</p>
      <form className="stack" style={{ gap: 8 }} onSubmit={(e) => { e.preventDefault(); run(); }}>
        <div className="grid-2">
          <label className="field">Sequence A<textarea className="input" rows={mode === "lines" ? 4 : 1} value={a} onChange={(e) => setA(e.target.value)} /></label>
          <label className="field">Sequence B<textarea className="input" rows={mode === "lines" ? 4 : 1} value={b} onChange={(e) => setB(e.target.value)} /></label>
        </div>
        <div className="row">
          <div className="chips" role="group" aria-label="Compare by">{["chars", "words", "lines"].map((m) => <button type="button" key={m} className="chip" aria-pressed={mode === m} onClick={() => setMode(m)}>{m}</button>)}</div>
          <button className="btn primary">Compute</button>
        </div>
      </form>
      <ErrorNote error={err} />
      {res && (
        <>
          <div className="note">LCS length <b>{res.length}</b>: <span className="mono">{res.lcs.join(mode === "chars" ? "" : mode === "words" ? " " : " ⏎ ") || "(none)"}</span></div>
          <DPTable hue={DS.lcs.hue} rows={["∅", ...res.a]} cols={["∅", ...res.b]} table={res.table} path={res.path}
            match={(i, j) => i > 0 && j > 0 && pathSet.has(`${i},${j}`) && res.a[i - 1] === res.b[j - 1]} caption="LCS table" />
          <span className="muted" style={{ fontSize: "0.82rem" }}>Shaded cells are the backtracking path; outlined cells are matches that form the LCS.</span>
        </>
      )}
    </div>
  );
}

// --- Edit distance ---
function EditTab() {
  const [a, setA] = useState("machne");
  const [b, setB] = useState("machine");
  const [res, setRes] = useState(null);
  const run = async () => { const r = await api.editDistance(a, b); setRes(r); trace("edit", `"${a}" -> "${b}": ${r.distance} edits`); };
  useEffect(() => { run(); }, []);
  const OPS = { "=": "keep", "~": "replace", "-": "delete", "+": "insert" };
  return (
    <div className="stack">
      <p className="muted" style={{ maxWidth: "70ch" }}>The minimum number of single-character inserts, deletes and replacements to turn A into B. Search uses it so “machne” still finds Machine_Learning files.</p>
      <form className="row" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <input className="input" value={a} onChange={(e) => setA(e.target.value)} aria-label="Word A" maxLength={40} />
        <input className="input" value={b} onChange={(e) => setB(e.target.value)} aria-label="Word B" maxLength={40} />
        <button className="btn primary">Compute</button>
      </form>
      {res && (
        <>
          <div className="note">Distance <b>{res.distance}</b>, similarity {(res.similarity * 100).toFixed(0)}%</div>
          <div className="chips mono">
            {res.alignment.map((o, i) => (
              <span key={i} className="tag" style={{ borderColor: o.op === "=" ? "var(--rule)" : "var(--edit)" }} title={OPS[o.op]}>
                {o.op === "=" ? o.a : o.op === "~" ? `${o.a}→${o.b}` : o.op === "-" ? `−${o.a}` : `+${o.b}`}
              </span>
            ))}
          </div>
          <DPTable hue={DS.edit.hue} rows={["∅", ...res.a]} cols={["∅", ...res.b]} table={res.table} caption="Edit distance table"
            path={res.path} />
        </>
      )}
    </div>
  );
}

// --- Knapsack ---
function KnapTab() {
  const [items, setItems] = useState([
    { label: "Report", weight: 4, value: 9 }, { label: "Slides", weight: 8, value: 7 },
    { label: "Notes", weight: 1, value: 8 }, { label: "Diagram", weight: 1, value: 5 }, { label: "Assignment", weight: 2, value: 10 },
  ]);
  const [cap, setCap] = useState(7);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const run = async () => {
    setErr(null);
    try {
      const r = await api.knapsack(items.map((i) => ({ ...i, weight: Number(i.weight), value: Number(i.value) })), Number(cap));
      setRes(r);
      trace("knap", `DP table ${r.table.length}×${r.capacity + 1}, best value ${r.best}`);
    } catch (e) { setErr(e); }
  };
  useEffect(() => { run(); }, []);
  const set = (k, field, v) => setItems(items.map((it, i) => (i === k ? { ...it, [field]: v } : it)));
  const takeRows = new Set((res?.path || []).filter((p) => p.take).map((p) => p.row));
  return (
    <div className="stack">
      <p className="muted" style={{ maxWidth: "70ch" }}>dp[i][w] is the best total value using the first i items with capacity w. Each cell either skips item i (copy from above) or takes it (value plus the cell w − weight to the left, one row up).</p>
      <form className="stack" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <table className="data" style={{ maxWidth: 520 }}>
          <thead><tr><th>Item</th><th>Weight</th><th>Value</th><th></th></tr></thead>
          <tbody>
            {items.map((it, k) => (
              <tr key={k}>
                <td><input className="input" value={it.label} onChange={(e) => set(k, "label", e.target.value)} aria-label="Item name" style={{ width: 130 }} /></td>
                <td><input className="input" type="number" min={0} max={50} value={it.weight} onChange={(e) => set(k, "weight", e.target.value)} aria-label="Weight" style={{ width: 80 }} /></td>
                <td><input className="input" type="number" min={0} max={100} value={it.value} onChange={(e) => set(k, "value", e.target.value)} aria-label="Value" style={{ width: 80 }} /></td>
                <td><button type="button" className="btn small ghost" onClick={() => setItems(items.filter((_, i) => i !== k))} aria-label="Remove item">×</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="row">
          <button type="button" className="btn small" disabled={items.length >= 12} onClick={() => setItems([...items, { label: `Item ${items.length + 1}`, weight: 1, value: 1 }])}>Add item</button>
          <label className="row muted">Capacity<input className="input" type="number" min={0} max={60} value={cap} onChange={(e) => setCap(e.target.value)} style={{ width: 80 }} /></label>
          <button className="btn primary">Solve</button>
        </div>
      </form>
      <ErrorNote error={err} />
      {res && (
        <>
          <div className="note">Best value <b>{res.best}</b> by taking {res.items.filter((_, i) => takeRows.has(i + 1)).map((i) => i.label).join(", ") || "nothing"}.</div>
          <DPTable hue={DS.knap.hue} rows={["none", ...res.items.map((i) => `${i.label} (${i.weight}, ${i.value})`)]} cols={Array.from({ length: res.capacity + 1 }, (_, w) => w)}
            table={res.table} path={res.path.filter((p) => p.take).map((p) => [p.row, p.col])} caption="Knapsack DP table" />
          <span className="muted" style={{ fontSize: "0.82rem" }}>Shaded cells are where an item was taken while tracing back from the bottom-right corner.</span>
          <table className="data" style={{ maxWidth: 640 }}>
            <thead><tr><th>Method</th><th className="num">Value</th><th className="num">Steps</th><th>Optimal</th></tr></thead>
            <tbody>{res.results.map((r) => <tr key={r.method} className={r.is_optimal ? "best" : ""}><td>{r.method}</td><td className="num">{r.total_value}</td><td className="num">{r.nodes_explored}</td><td>{r.is_optimal ? "Yes" : "No"}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </div>
  );
}

const VIEWS = { avl: AVLTab, hash: HashTab, trie: TrieTab, heap: HeapTab, merkle: MerkleTab, lcs: LCSTab, edit: EditTab, knap: KnapTab };

export default function ExplorerPage({ initialTab }) {
  const [tab, setTab] = useState(initialTab && VIEWS[initialTab] ? initialTab : "avl");
  const View = VIEWS[tab];
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["avl", "hash", "trie", "heap", "merkle", "lcs", "edit", "knap"]} />
          <h1>Algorithm explorer</h1>
          <p>See inside each structure. Use your real files, or try your own input in the sandbox and step through it one operation at a time.</p>
        </div>
      </div>
      <div className="tabs" role="tablist" style={{ padding: 0, marginBottom: 18, marginTop: 0 }}>
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} style={{ "--tab-hue": DS[t.ds].hue }} onClick={() => { setTab(t.id); history.replaceState(null, "", `#/explorer/${t.id}`); }}>
            {DS[t.ds].name}
          </button>
        ))}
      </div>
      <section className="panel panel-pad" role="tabpanel">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}><DSLabel ds={TABS.find((t) => t.id === tab).ds} /><span className="muted mono">{DS[TABS.find((t) => t.id === tab).ds].cost}</span></div>
        <View key={tab} />
      </section>
    </>
  );
}
