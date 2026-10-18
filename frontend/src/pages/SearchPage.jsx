import { useEffect, useState } from "react";
import { api, trace } from "../api.js";
import { DSLabel, ErrorNote, FileBadge, Took, PageUses } from "../components/Common.jsx";
import { Search } from "../components/Icons.jsx";

function highlight(text, terms) {
  if (!text || !terms?.length) return text;
  const re = new RegExp(`\\b(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\w*`, "gi");
  const out = []; let last = 0, m;
  while ((m = re.exec(text))) { out.push(text.slice(last, m.index), <mark key={m.index}>{m[0]}</mark>); last = m.index + m[0].length; }
  out.push(text.slice(last));
  return out;
}

function Column({ ds, title, how, took, results, render, empty }) {
  return (
    <section className="panel" aria-label={title}>
      <div className="panel-head"><div className="stack" style={{ gap: 2 }}><DSLabel ds={ds}>{title}</DSLabel><span className="muted" style={{ fontSize: "0.82rem" }}>{how}</span></div><Took ms={took} /></div>
      {results.length === 0 ? <div className="empty" style={{ padding: 24 }}>{empty}</div> : <ul className="results">{results.map(render)}</ul>}
    </section>
  );
}

export default function SearchPage({ initial, openFile }) {
  const [text, setText] = useState(initial || "");
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const run = async (q) => {
    if (!q.trim()) return;
    setErr(null);
    try {
      const r = await api.search(q.trim());
      setRes(r);
      trace("trie", `prefix "${r.query}" -> ${r.prefix.results.length}`, r.prefix.took_ms);
      trace("edit", `fuzzy match "${r.query}" -> ${r.fuzzy.results.length}`, r.fuzzy.took_ms);
      trace("ai", `TF-IDF rank "${r.query}" -> ${r.semantic.results.length}`, r.semantic.took_ms);
    } catch (e) { setErr(e); }
  };
  useEffect(() => { if (initial) { setText(initial); run(initial); } }, [initial]);
  const open = (f) => (
    <button className="linkish" onClick={() => openFile(f.file_id)}>
      <span className="fname"><FileBadge file={f} /><span>{f.filename}</span></span>
    </button>
  );
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["trie", "edit", "ai"]} />
          <h1>Search</h1>
          <p>One query, three algorithms. The Trie matches the start of a name, edit distance forgives typos, and TF-IDF finds files by what is written inside them.</p>
        </div>
      </div>
      <form className="toolbar" onSubmit={(e) => { e.preventDefault(); run(text); }}>
        <div className="search-box"><Search /><input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Try “machne”, “lecture” or “supervised learning”" aria-label="Search query" /></div>
        <button className="btn primary">Search</button>
      </form>
      <ErrorNote error={err} />
      {res?.did_you_mean && (
        <div className="note" style={{ marginBottom: 14 }}>
          Nothing matched. Did you mean <button className="btn small" onClick={() => { setText(res.did_you_mean); run(res.did_you_mean); }}>{res.did_you_mean}</button>?
        </div>
      )}
      {res && (
        <div className="grid-3">
          <Column ds="trie" title="Prefix (Trie)" how="Walks one node per character, then collects every word below." took={res.prefix.took_ms}
            results={res.prefix.results} empty="No filename starts with this."
            render={(f) => <li key={f.file_id}>{open(f)}</li>} />
          <Column ds="edit" title="Typo-tolerant (edit distance)" how="Levenshtein DP between your query and each word of each filename." took={res.fuzzy.took_ms}
            results={res.fuzzy.results} empty="No name within a few edits."
            render={(f) => <li key={f.file_id}>{open(f)}<span className="snippet">{f.distance === 0 ? `exact ${f.method === "trie-prefix" ? "prefix" : "substring"}` : `${f.distance} edit${f.distance > 1 ? "s" : ""} from “${f.matched}”`}</span></li>} />
          <Column ds="ai" title="By content (TF-IDF)" how="Cosine similarity over an inverted index of every word in your files." took={res.semantic.took_ms}
            results={res.semantic.results} empty="No file mentions these words."
            render={(f) => <li key={f.file_id}>{open(f)}<span className="snippet">{f.snippet ? highlight(f.snippet, f.matched_terms) : `matched: ${f.matched_terms.join(", ")}`}</span><span className="snippet mono">score {f.score}</span></li>} />
        </div>
      )}
      {!res && !err && <div className="empty">Search runs all three methods at once so you can compare them side by side.</div>}
    </>
  );
}
