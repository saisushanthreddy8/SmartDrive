import { useEffect, useRef, useState } from "react";
import { api, changed, DS, fmtBytes, fmtDate, short, toast, trace } from "../api.js";
import { DSLabel, ErrorNote, Meter, useAsync, useLive } from "../components/Common.jsx";
import { Close, Download, Shield, Trash, Upload } from "../components/Icons.jsx";

const TABS = [
  { id: "details", label: "Details", hue: "var(--ink)" },
  { id: "versions", label: "Versions", hue: DS.lcs.hue },
  { id: "integrity", label: "Integrity", hue: DS.merkle.hue },
  { id: "ai", label: "AI insights", hue: DS.ai.hue },
];

function Preview({ file }) {
  const p = useAsync(() => api.preview(file.file_id), [file.file_id, file.current_version]);
  if (p.loading && !p.data) return <div className="muted">Loading preview…</div>;
  if (p.error) return <ErrorNote error={p.error} />;
  const src = api.downloadUrl(file.file_id, null, true) + `&v=${file.current_version}`;
  const k = p.data.kind;
  if (k === "image") return <img className="preview-media" src={src} alt={`Preview of ${file.filename}`} />;
  if (k === "audio") return <audio controls src={src} style={{ width: "100%" }} />;
  if (k === "video") return <video controls src={src} className="preview-media" />;
  if (k === "pdf") return <a className="btn small" href={src} target="_blank" rel="noreferrer">Open PDF in a new tab</a>;
  if (k === "text") return <pre className="preview">{p.data.text || "(empty file)"}{p.data.truncated ? "\n…" : ""}</pre>;
  return <div className="note">No preview for this file type. Download it to open.</div>;
}

function Details({ file, onDeleted }) {
  const [priority, setPriority] = useState(file.priority);
  const [description, setDescription] = useState(file.description || "");
  const [tags, setTags] = useState(file.tags);
  const [tagText, setTagText] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const dirty = priority !== file.priority || description !== (file.description || "") || tags.join("|") !== file.tags.join("|");

  const save = async () => {
    try {
      await api.editMeta(file.file_id, { priority, description, tags });
      if (priority !== file.priority) trace("heap", `remove + re-insert "${file.filename}" at priority ${priority}`);
      toast("Changes saved");
      changed();
    } catch (e) { toast(e.message, true); }
  };
  const addTag = (e) => {
    e.preventDefault();
    const t = tagText.trim();
    if (t && !tags.some((x) => x.toLowerCase() === t.toLowerCase())) setTags([...tags, t]);
    setTagText("");
  };
  const del = async () => {
    try {
      const r = await api.remove(file.file_id);
      ["avl", "hash", "trie", "heap"].forEach((d) => trace(d, `delete "${file.filename}"`));
      trace("disk", "removed file and version snapshots");
      trace("merkle", `root rebuilt -> ${short(r.merkle_root, 12)}`);
      toast(`Deleted ${file.filename}`);
      changed(); onDeleted();
    } catch (e) { toast(e.message, true); }
  };

  return (
    <>
      <Preview file={file} />
      <dl className="kv">
        <dt>Size</dt><dd>{file.formatted_size} ({file.file_size.toLocaleString()} bytes)</dd>
        <dt>Type</dt><dd>{file.file_type}</dd>
        <dt>Uploaded</dt><dd>{fmtDate(file.upload_date)}</dd>
        <dt>Stored at</dt><dd className="mono">storage/{file.storage_path}</dd>
        <dt>SHA-256</dt><dd className="hash">{file.sha256_hash}</dd>
      </dl>
      <label className="field">
        Priority: {priority}
        <input type="range" min={1} max={10} value={priority} onChange={(e) => setPriority(Number(e.target.value))} style={{ accentColor: "var(--heap)" }} />
      </label>
      <label className="field">Description<input className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What is this file for?" /></label>
      <div className="field" style={{ display: "grid", gap: 6 }}>
        <span className="muted" style={{ fontSize: "0.86rem" }}>Tags</span>
        <div className="chips">
          {tags.map((t) => <span className="tag" key={t}>{t}<button aria-label={`Remove tag ${t}`} onClick={() => setTags(tags.filter((x) => x !== t))}>×</button></span>)}
          <form onSubmit={addTag}><input className="input" style={{ padding: "2px 8px", width: 120 }} value={tagText} onChange={(e) => setTagText(e.target.value)} placeholder="Add tag" aria-label="Add tag" /></form>
        </div>
      </div>
      <div className="row">
        <button className="btn primary" disabled={!dirty} onClick={save}>Save changes</button>
        <a className="btn" href={api.downloadUrl(file.file_id)}><Download /> Download</a>
        <span className="grow" />
        {confirmDelete
          ? <><button className="btn danger" onClick={del}>Delete permanently</button><button className="btn ghost" onClick={() => setConfirmDelete(false)}>Keep</button></>
          : <button className="btn danger" onClick={() => setConfirmDelete(true)}><Trash /> Delete</button>}
      </div>
    </>
  );
}

function Versions({ file }) {
  const latest = file.current_version;
  const [v1, setV1] = useState(Math.max(1, latest - 1));
  const [v2, setV2] = useState(latest);
  const [diff, setDiff] = useState(null);
  const [err, setErr] = useState(null);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  const fileInput = useRef(null);

  const compare = async (a = v1, b = v2) => {
    setErr(null);
    try {
      const d = await api.diff(file.file_id, a, b);
      setDiff(d);
      if (!d.binary) trace("lcs", `diff v${a} -> v${b}: ${d.table_size[0]}×${d.table_size[1]} table, LCS ${d.lcs_length} lines`, d.took_ms);
    } catch (e) { setErr(e); }
  };
  useEffect(() => {
    setV1(Math.max(1, latest - 1)); setV2(latest);
    if (latest > 1) compare(Math.max(1, latest - 1), latest); else setDiff(null);
  }, [file.file_id, latest]);

  const startEdit = async () => {
    try { const p = await api.preview(file.file_id); setText(p.kind === "text" ? p.text : ""); } catch { setText(""); }
    setEditing(true);
  };
  const afterVersion = (res, how) => {
    trace("disk", `snapshot storage/versions/…/v${res.new_version}_${file.filename}`);
    trace("merkle", `leaf hash changed -> root ${short(res.merkle_root, 12)}`);
    toast(`${how}: now version ${res.new_version}`);
    setEditing(false); setNote(""); changed();
  };
  const saveText = async () => {
    try { afterVersion(await api.textVersion(file.file_id, text, note), "Saved"); } catch (e) { toast(e.message, true); }
  };
  const uploadVersion = async (f) => {
    try { afterVersion(await api.uploadVersion(file.file_id, f, note || `Uploaded ${f.name}`), "Uploaded"); } catch (e) { toast(e.message, true); }
  };
  const rollback = async (v) => {
    try { afterVersion(await api.rollback(file.file_id, v), `Restored v${v}`); } catch (e) { toast(e.message, true); }
  };

  const opts = file.version_history.map((v) => v.version_number);
  return (
    <>
      <div className="row">
        <button className="btn" onClick={startEdit}>Edit as text</button>
        <button className="btn" onClick={() => fileInput.current.click()}><Upload /> Upload new version</button>
        <input ref={fileInput} type="file" hidden onChange={(e) => { e.target.files[0] && uploadVersion(e.target.files[0]); e.target.value = ""; }} />
      </div>
      {editing && (
        <div className="stack">
          <textarea className="input" rows={9} value={text} onChange={(e) => setText(e.target.value)} aria-label="File content" />
          <input className="input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What changed? (version note)" />
          <div className="row"><button className="btn primary" onClick={saveText}>Save as version {latest + 1}</button><button className="btn ghost" onClick={() => setEditing(false)}>Cancel</button></div>
        </div>
      )}
      <ul className="versions">
        {[...file.version_history].reverse().map((v) => (
          <li key={v.version_number}>
            <span className="vnum">v{v.version_number}</span>
            <span><span>{v.description || "No note"}</span><br /><span className="muted" style={{ fontSize: "0.8rem" }}>{fmtBytes(v.file_size)}, {fmtDate(v.timestamp)}, <span className="mono">{short(v.sha256_hash, 8)}</span></span></span>
            <span className="row" style={{ gap: 4 }}>
              <a className="btn small ghost" href={api.downloadUrl(file.file_id, v.version_number)} aria-label={`Download version ${v.version_number}`}><Download /></a>
              {v.version_number !== latest && <button className="btn small" onClick={() => rollback(v.version_number)}>Restore</button>}
            </span>
          </li>
        ))}
      </ul>
      {latest > 1 ? (
        <div className="stack" style={{ gap: 10 }}>
          <div className="row">
            <DSLabel ds="lcs">Compare with LCS</DSLabel>
            <select className="input" value={v1} onChange={(e) => setV1(Number(e.target.value))} aria-label="Older version">{opts.map((o) => <option key={o} value={o}>v{o}</option>)}</select>
            <span className="muted">to</span>
            <select className="input" value={v2} onChange={(e) => setV2(Number(e.target.value))} aria-label="Newer version">{opts.map((o) => <option key={o} value={o}>v{o}</option>)}</select>
            <button className="btn small" onClick={() => compare()}>Compare</button>
          </div>
          <ErrorNote error={err} />
          {diff && diff.binary && <div className="note">Binary file: v{diff.v1} and v{diff.v2} are {diff.identical ? "identical" : "different"} ({fmtBytes(diff.sizes[0])} vs {fmtBytes(diff.sizes[1])}). A line diff needs text.</div>}
          {diff && !diff.binary && (
            <>
              <div className="row" style={{ fontSize: "0.88rem", gap: 14 }}>
                <span style={{ color: "var(--ok)" }}>+{diff.stats.added} added</span>
                <span style={{ color: "var(--danger)" }}>−{diff.stats.removed} removed</span>
                <span className="muted">{diff.stats.unchanged} unchanged</span>
                <span className="muted">LCS {diff.lcs_length} lines</span>
              </div>
              <div><div className="row muted" style={{ justifyContent: "space-between", fontSize: "0.82rem" }}><span>Similarity</span><span>{diff.stats.similarity_pct}%</span></div><Meter pct={diff.stats.similarity_pct} hue="var(--lcs)" /></div>
              <div className="diff" aria-label="Line diff">
                {diff.diff.length === 0 && <div className="muted">Both versions are empty.</div>}
                {diff.diff.map((d, i) => <div key={i} className={d.op === "+" ? "add" : d.op === "-" ? "del" : ""}>{d.text || " "}</div>)}
              </div>
            </>
          )}
        </div>
      ) : <div className="note">Only one version so far. Edit or upload a new version to compare them with LCS.</div>}
    </>
  );
}

function Integrity({ file }) {
  const [res, setRes] = useState(null);
  const verify = async () => {
    try {
      const r = await api.verify(file.file_id);
      setRes(r);
      trace("merkle", `verify "${file.filename}": ${r.proof.length}-step audit proof, ${r.valid ? "valid" : "FAILED"}`);
    } catch (e) { toast(e.message, true); }
  };
  useEffect(() => { verify(); }, [file.file_id, file.current_version]);
  const tamper = async () => {
    try { await api.tamper(file.file_id); trace("disk", `wrote bytes into ${file.filename} outside SmartDrive`); toast("File changed on disk. Verify to catch it."); setRes(null); }
    catch (e) { toast(e.message, true); }
  };
  const repair = async () => {
    try { const r = await api.repair(file.file_id); trace("disk", `restored from snapshot v${file.current_version}`); toast(r.message); verify(); changed(); }
    catch (e) { toast(e.message, true); }
  };
  return (
    <>
      <p className="muted" style={{ fontSize: "0.9rem" }}>SmartDrive re-reads the file from disk, hashes it with SHA-256, and checks that hash against its leaf in the Merkle tree. The audit proof rebuilds the path up to the root.</p>
      <div className="row">
        <button className="btn primary" onClick={verify}><Shield /> Verify now</button>
        <button className="btn" onClick={tamper}>Simulate tampering</button>
        {res && !res.valid && <button className="btn" onClick={repair}>Repair from snapshot</button>}
      </div>
      {res && (
        <>
          <div className={`note ${res.valid ? "ok" : "bad"}`}>{res.message}</div>
          <dl className="kv">
            <dt>Expected</dt><dd className="hash">{res.expected_hash}</dd>
            <dt>On disk</dt><dd className="hash" style={{ color: res.disk_hash === res.expected_hash ? "var(--ok)" : "var(--danger)" }}>{res.disk_hash || "missing"}</dd>
          </dl>
          {res.proof.length > 0 && (
            <div className="stack" style={{ gap: 8 }}>
              <DSLabel ds="merkle">Audit proof, leaf to root</DSLabel>
              <ol className="proof">
                {res.proof.map((s, i) => (
                  <li key={i}>
                    <span className="muted">hash(</span>{s.side === "left" ? <span className="mono">sibling {short(s.sibling, 8)} + current</span> : <span className="mono">current + sibling {short(s.sibling, 8)}</span>}<span className="muted">)</span>
                    <br /><span className="mono">= {short(s.result, 16)}</span>
                  </li>
                ))}
              </ol>
              <div className={`note ${res.root_matches ? "ok" : "bad"}`}>
                Recomputed root <span className="mono">{short(res.recomputed_root, 12)}</span> {res.root_matches ? "matches" : "does not match"} the stored root <span className="mono">{short(res.root, 12)}</span>.
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

function Insights({ file, onSelect }) {
  const ins = useAsync(() => api.insights(file.file_id), [file.file_id, file.current_version, file.tags.join("|"), file.priority]);
  useEffect(() => { if (ins.data) trace("ai", `insights for "${file.filename}": ${ins.data.keywords.length} keywords, ${ins.data.similar.length} similar files`); }, [ins.data]);
  const apply = async (body, msg) => {
    try { await api.applyAI(file.file_id, body); if (body.priority) trace("heap", `re-insert at suggested priority`); toast(msg); changed(); }
    catch (e) { toast(e.message, true); }
  };
  if (ins.loading && !ins.data) return <div className="muted">Reading the file…</div>;
  if (ins.error) return <ErrorNote error={ins.error} />;
  const d = ins.data;
  const newTags = d.tags.filter((t) => !file.tags.includes(t.tag));
  return (
    <>
      <p className="muted" style={{ fontSize: "0.88rem" }}>Runs offline on this computer: TF-IDF weighting, an inverted index and cosine similarity. No data leaves SmartDrive.</p>
      {!d.has_text && <div className="note">No readable text in this file, so insights use the filename, description and tags only.</div>}
      {d.has_text && <div className="muted" style={{ fontSize: "0.85rem" }}>{d.stats.words.toLocaleString()} words, {d.stats.lines.toLocaleString()} lines, about {d.stats.reading_minutes} min to read</div>}
      {d.summary.length > 0 && (
        <div className="stack" style={{ gap: 6 }}>
          <h3>Summary</h3>
          <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 4 }}>{d.summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {d.keywords.length > 0 && (
        <div className="stack" style={{ gap: 6 }}>
          <h3>Keywords</h3>
          <div className="chips">{d.keywords.map((k) => <span className="tag" key={k.term} title={`TF-IDF weight ${k.weight}`}>{k.term}</span>)}</div>
        </div>
      )}
      <div className="stack" style={{ gap: 6 }}>
        <div className="row" style={{ justifyContent: "space-between" }}><h3>Suggested tags</h3>{newTags.length > 0 && <button className="btn small" onClick={() => apply({ tags: true, priority: false }, "Tags added")}>Add {newTags.length === 1 ? "tag" : "all"}</button>}</div>
        {d.tags.length === 0 ? <span className="muted">No confident tag.</span> : (
          <ul className="results" style={{ border: "1px solid var(--rule)", borderRadius: 5 }}>
            {d.tags.map((t) => <li key={t.tag}><span>{t.tag}{file.tags.includes(t.tag) && <span className="muted"> (added)</span>}</span><span className="snippet">because of: {t.evidence.join(", ")}</span></li>)}
          </ul>
        )}
      </div>
      <div className="stack" style={{ gap: 6 }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h3>Suggested priority: {d.priority.suggested}</h3>
          {d.priority.suggested !== file.priority && <button className="btn small" onClick={() => apply({ tags: false, priority: true }, `Priority set to ${d.priority.suggested}`)}>Use {d.priority.suggested} (now {file.priority})</button>}
        </div>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.88rem", color: "var(--muted)" }}>{d.priority.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      </div>
      {d.similar.length > 0 && (
        <div className="stack" style={{ gap: 6 }}>
          <h3>Similar files</h3>
          <ul className="results" style={{ border: "1px solid var(--rule)", borderRadius: 5 }}>
            {d.similar.map((s) => (
              <li key={s.file.file_id}>
                <button className="linkish" onClick={() => onSelect(s.file.file_id)}>{s.file.filename}</button>
                <span className="snippet">cosine similarity {(s.score * 100).toFixed(0)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

export default function FilePanel({ fileId, onClose, onSelect }) {
  const [tab, setTab] = useState("details");
  const f = useLive(() => api.file(fileId), [fileId]);
  useEffect(() => {
    if (f.data) trace("hash", `lookup by id -> "${f.data.filename}"`);
  }, [f.data?.file_id]);
  if (f.error) return <aside className="panel detail"><div className="detail-body"><ErrorNote error={f.error} /><button className="btn" onClick={onClose}>Close</button></div></aside>;
  if (!f.data) return <aside className="panel detail"><div className="detail-body muted">Loading…</div></aside>;
  const file = f.data;
  return (
    <aside className="panel detail" aria-label={`Details for ${file.filename}`}>
      <div className="detail-head">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", flexWrap: "nowrap" }}>
          <h2>{file.filename}</h2>
          <button className="btn ghost small" onClick={onClose} aria-label="Close details"><Close /></button>
        </div>
        <div className="muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>Version {file.current_version}, priority {file.priority}{file.tags.length ? `, tagged ${file.tags.join(", ")}` : ""}</div>
      </div>
      <div className="tabs" role="tablist">
        {TABS.map((t) => <button key={t.id} role="tab" aria-selected={tab === t.id} style={{ "--tab-hue": t.hue }} onClick={() => setTab(t.id)}>{t.label}</button>)}
      </div>
      <div className="detail-body" role="tabpanel">
        {tab === "details" && <Details key={`${file.priority}|${file.description}|${file.tags.join("|")}`} file={file} onDeleted={onClose} />}
        {tab === "versions" && <Versions file={file} />}
        {tab === "integrity" && <Integrity file={file} />}
        {tab === "ai" && <Insights file={file} onSelect={onSelect} />}
      </div>
    </aside>
  );
}
