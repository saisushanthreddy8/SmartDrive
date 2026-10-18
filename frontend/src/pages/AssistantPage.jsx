import { useState } from "react";
import { api, fmtBytes, trace } from "../api.js";
import { DSLabel, ErrorNote, FileBadge, Took, useLive, PageUses } from "../components/Common.jsx";

const EXAMPLES = ["What is supervised learning?", "When is the assignment deadline?", "What detects tampering?", "How does extract max work?"];

function Pair({ files, openFile, right }) {
  return (
    <li style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center" }}>
      <span className="stack" style={{ gap: 4 }}>
        {files.map((f) => <button key={f.file_id} className="linkish" onClick={() => openFile(f.file_id)}><span className="fname"><FileBadge file={f} /><span>{f.filename}</span></span></button>)}
      </span>
      <span className="muted mono" style={{ fontSize: "0.85rem" }}>{right}</span>
    </li>
  );
}

export default function AssistantPage({ openFile }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const dups = useLive(() => api.duplicates());
  const ask = async (q) => {
    if (!q.trim()) return;
    setQuestion(q); setBusy(true); setErr(null);
    try {
      const r = await api.ask(q.trim());
      setAnswer(r);
      trace("ai", `answered from ${new Set(r.answers.map((a) => a.file.file_id)).size} file(s) using terms: ${r.terms.join(", ") || "none"}`, r.took_ms);
    } catch (e) { setErr(e); }
    setBusy(false);
  };
  const d = dups.data;
  const dupCount = d ? d.exact.length + d.near.length + d.similar_names.length : 0;
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["ai", "edit"]} />
          <h1>AI assistant</h1>
          <p>Ask a question about what is inside your files. Answers are sentences pulled from your own documents and ranked by TF-IDF similarity. Everything runs on this computer, with no API key and no internet.</p>
        </div>
      </div>
      <section className="panel panel-pad stack" style={{ marginBottom: 18 }}>
        <form className="row" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
          <input className="input grow" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about your files" aria-label="Question" maxLength={500} />
          <button className="btn primary" disabled={busy || !question.trim()}>{busy ? "Searching…" : "Ask"}</button>
        </form>
        <div className="chips">{EXAMPLES.map((q) => <button key={q} className="chip" onClick={() => ask(q)}>{q}</button>)}</div>
        <ErrorNote error={err} />
        {answer && (
          answer.found ? (
            <div className="stack" style={{ gap: 10 }}>
              <div className="row" style={{ justifyContent: "space-between" }}><DSLabel ds="ai">Best matching passages</DSLabel><Took ms={answer.took_ms} /></div>
              {answer.answers.map((a, i) => (
                <blockquote key={i} style={{ margin: 0, padding: "10px 14px", borderLeft: "3px solid var(--ai)", background: "var(--surface-2)", borderRadius: "0 5px 5px 0" }}>
                  <p>{a.text}</p>
                  <div className="row muted" style={{ fontSize: "0.82rem", marginTop: 6, justifyContent: "space-between" }}>
                    <button className="linkish btn ghost small" onClick={() => openFile(a.file.file_id)}>From {a.file.filename}</button>
                    <span className="mono">relevance {a.score}</span>
                  </div>
                </blockquote>
              ))}
            </div>
          ) : <div className="note">None of your files mention {answer.terms.length ? answer.terms.map((t) => `“${t}”`).join(", ") : "those words"}. Try different words, or upload a file that covers the topic.</div>
        )}
      </section>

      <section className="panel">
        <div className="panel-head">
          <DSLabel ds="ai">Duplicates and near-duplicates</DSLabel>
          {d && d.wasted_bytes > 0 && <span className="muted">{fmtBytes(d.wasted_bytes)} could be freed</span>}
        </div>
        <ErrorNote error={dups.error} />
        {d && dupCount === 0 && <div className="empty">No duplicates found. Each file has different content and a distinct name.</div>}
        {d && dupCount > 0 && (
          <div className="grid-3 panel-pad">
            <div className="stack" style={{ gap: 6 }}>
              <h3>Identical content</h3><span className="muted" style={{ fontSize: "0.82rem" }}>Same SHA-256 hash</span>
              {d.exact.length ? <ul className="results">{d.exact.map((g) => <Pair key={g.sha256} files={g.files} openFile={openFile} right={fmtBytes(g.wasted_bytes)} />)}</ul> : <span className="muted">None</span>}
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <h3>Nearly the same text</h3><span className="muted" style={{ fontSize: "0.82rem" }}>TF-IDF cosine similarity of 85% or more</span>
              {d.near.length ? <ul className="results">{d.near.map((g, i) => <Pair key={i} files={g.files} openFile={openFile} right={`${Math.round(g.similarity * 100)}%`} />)}</ul> : <span className="muted">None</span>}
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <h3>Similar names</h3><span className="muted" style={{ fontSize: "0.82rem" }}>Edit distance similarity of 80% or more</span>
              {d.similar_names.length ? <ul className="results">{d.similar_names.map((g, i) => <Pair key={i} files={g.files} openFile={openFile} right={`${Math.round(g.similarity * 100)}%`} />)}</ul> : <span className="muted">None</span>}
            </div>
          </div>
        )}
      </section>
      <p className="muted" style={{ fontSize: "0.85rem", marginTop: 14 }}>Open any file and choose AI insights for its summary, keywords, suggested tags and suggested priority.</p>
    </>
  );
}
