import { useEffect, useRef, useState } from "react";
import { api, changed, fmtBytes, fmtDate, toast, trace, short } from "../api.js";
import { ErrorNote, FileBadge, Priority, useLive, PageUses } from "../components/Common.jsx";
import { Plus, Search, Upload } from "../components/Icons.jsx";
import FilePanel from "./FilePanel.jsx";

const TYPES = ["All", "Document", "Image", "Video", "Audio", "Archive", "Other"];
const COLUMNS = [
  { key: "name", label: "Name" },
  { key: "type", label: "Type", noSort: true, cls: "hide-sm hide-detail" },
  { key: "size", label: "Size", num: true },
  { key: "priority", label: "Priority" },
  { key: "versions", label: "Versions", num: true, cls: "hide-sm" },
  { key: "date", label: "Uploaded", cls: "hide-sm hide-detail" },
];

export function traceInsert(file, root) {
  trace("disk", `saved storage/${file.storage_path}`);
  trace("avl", `insert "${file.filename}" (self-balancing)`);
  trace("hash", `insert by name + by id`);
  trace("trie", `insert ${file.filename.length} characters`);
  trace("heap", `insert priority ${file.priority}, sift up`);
  trace("merkle", `root rebuilt -> ${short(root, 12)}`);
}

function StatLine() {
  const stats = useLive(() => api.stats());
  const data = stats.data;
  if (!data) return null;
  return (
    <div className="statline">
      <div style={{ "--hue": "var(--ink)" }}><b>{data.total_files}</b><span>files, {fmtBytes(data.total_bytes)}</span></div>
      <div style={{ "--hue": "var(--lcs)" }}><b>{data.total_versions}</b><span>versions stored</span></div>
      <div style={{ "--hue": "var(--avl)" }}><b>{data.avl.height}</b><span>AVL height (best {data.avl.optimal_height})</span></div>
      <div style={{ "--hue": "var(--hash)" }}><b>{data.hash_table.load_factor}</b><span>hash load factor</span></div>
      <div style={{ "--hue": "var(--trie)" }}><b>{data.trie.nodes}</b><span>trie nodes</span></div>
      <div style={{ "--hue": "var(--merkle)" }}><b className="mono">{short(data.merkle.root, 8)}</b><span>Merkle root</span></div>
    </div>
  );
}

function SearchBox({ onPick, onSearch }) {
  const [text, setText] = useState("");
  const [sugs, setSugs] = useState([]);
  const [meta, setMeta] = useState(null);
  const [active, setActive] = useState(-1);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!text.trim()) { setSugs([]); return; }
    const t = setTimeout(() => {
      api.autocomplete(text.trim()).then((r) => {
        setSugs(r.suggestions); setMeta(r); setActive(-1); setOpen(true);
        trace("trie", `autocomplete "${text.trim()}" -> ${r.suggestions.length} match${r.suggestions.length === 1 ? "" : "es"}`, r.took_ms);
      }).catch(() => {});
    }, 140);
    return () => clearTimeout(t);
  }, [text]);
  const pick = (s) => { setOpen(false); setText(""); onPick(s.file_id); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, sugs.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, -1)); }
    else if (e.key === "Escape") setOpen(false);
    else if (e.key === "Enter") {
      if (active >= 0 && sugs[active]) pick(sugs[active]);
      else if (text.trim()) { setOpen(false); onSearch(text.trim()); }
    }
  };
  return (
    <div className="search-box" role="combobox" aria-expanded={open && sugs.length > 0} aria-haspopup="listbox">
      <Search />
      <input className="input" placeholder="Type a filename prefix, press Enter for full search" value={text}
        onChange={(e) => setText(e.target.value)} onKeyDown={onKey} onBlur={() => setTimeout(() => setOpen(false), 150)}
        onFocus={() => sugs.length && setOpen(true)} aria-label="Search files" aria-autocomplete="list" />
      {open && text.trim() && (
        <div className="suggest" role="listbox">
          {sugs.map((s, i) => (
            <button key={s.file_id} role="option" aria-selected={i === active} onMouseDown={() => pick(s)}>
              <span>{s.filename}</span><span className="muted">{s.file_type}</span>
            </button>
          ))}
          <div className="suggest-foot">
            {sugs.length ? `Trie prefix walk in ${meta ? (meta.took_ms < 1 ? Math.round(meta.took_ms * 1000) + " µs" : meta.took_ms + " ms") : ""}. ` : "No filename starts with that. "}
            Press Enter for fuzzy and AI search.
          </div>
        </div>
      )}
    </div>
  );
}

function NewTextFile({ onDone }) {
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState(5);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.createText({ filename: name.trim(), content, priority: Number(priority) });
      traceInsert(res.file, res.merkle_root);
      toast(`Created ${res.file.filename}`);
      changed(); onDone(res.file_id);
    } catch (err) { toast(err.message, true); }
    setBusy(false);
  };
  return (
    <form className="panel panel-pad stack" onSubmit={submit} style={{ marginBottom: 14 }}>
      <div className="row">
        <label className="field grow">File name<input className="input" required value={name} onChange={(e) => setName(e.target.value)} placeholder="meeting_notes.txt" /></label>
        <label className="field">Priority<input className="input" type="number" min={1} max={10} value={priority} onChange={(e) => setPriority(e.target.value)} style={{ width: 80 }} /></label>
      </div>
      <label className="field">Content<textarea className="input" rows={6} value={content} onChange={(e) => setContent(e.target.value)} /></label>
      <div className="row"><button className="btn primary" disabled={busy || !name.trim()}>Create file</button><button type="button" className="btn ghost" onClick={() => onDone(null)}>Cancel</button></div>
    </form>
  );
}

export default function Drive({ selected, setSelected, goSearch }) {
  const [type, setType] = useState("All");
  const [sort, setSort] = useState({ key: "name", order: "asc" });
  const [over, setOver] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploadPrio, setUploadPrio] = useState(5);
  const fileInput = useRef(null);
  const list = useLive(() => api.files({ file_type: type === "All" ? null : type, sort: sort.key, order: sort.order }), [type, sort.key, sort.order]);
  useEffect(() => {
    if (list.data && sort.key === "name" && type === "All") trace("avl", `in-order traversal -> ${list.data.count} files, already sorted`, list.data.took_ms);
  }, [list.data]);

  const uploadFiles = async (files) => {
    for (const f of files) {
      try {
        const res = await api.upload(f, { priority: uploadPrio });
        traceInsert(res.file, res.merkle_root);
        toast(`Uploaded ${res.file.filename}`);
        setSelected(res.file_id);
      } catch (err) { toast(`${f.name}: ${err.message}`, true); }
    }
    changed();
  };

  const header = (c) => {
    if (c.noSort) return c.label;
    const activeSort = sort.key === c.key;
    return (
      <button onClick={() => setSort({ key: c.key, order: activeSort && sort.order === "asc" ? "desc" : "asc" })}
        aria-label={`Sort by ${c.label}`}>
        {c.label}{activeSort ? (sort.order === "asc" ? " ↑" : " ↓") : ""}
      </button>
    );
  };

  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["avl", "hash", "trie", "heap", "merkle"]} />
          <h1>Drive</h1>
          <p>Your files, stored on disk in <span className="mono">storage/</span>. Every list, lookup and search below runs on a data structure built from scratch.</p>
        </div>
      </div>
      <StatLine />
      <div className={`drive ${selected ? "has-detail" : ""}`}>
        <div style={{ minWidth: 0 }}>
          <div className="toolbar">
            <SearchBox onPick={setSelected} onSearch={goSearch} />
            <label className="row muted" style={{ gap: 6, fontSize: "0.86rem" }}>
              Priority
              <select className="input" value={uploadPrio} onChange={(e) => setUploadPrio(Number(e.target.value))} aria-label="Priority for new uploads">
                {Array.from({ length: 10 }, (_, i) => i + 1).map((p) => <option key={p}>{p}</option>)}
              </select>
            </label>
            <button className="btn primary" onClick={() => fileInput.current.click()}><Upload /> Upload</button>
            <button className="btn" onClick={() => setCreating((c) => !c)}><Plus /> New text file</button>
            <input ref={fileInput} type="file" multiple hidden onChange={(e) => { uploadFiles([...e.target.files]); e.target.value = ""; }} />
          </div>
          {creating && <NewTextFile onDone={(id) => { setCreating(false); if (id) setSelected(id); }} />}
          <div className={`dropzone ${over ? "over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); uploadFiles([...e.dataTransfer.files]); }}>
            Drop files here to upload them with priority {uploadPrio}
          </div>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <div className="chips" role="group" aria-label="Filter by type">
              {TYPES.map((t) => <button key={t} className="chip" aria-pressed={type === t} onClick={() => setType(t)}>{t}</button>)}
            </div>
            {list.data && <span className="muted" style={{ fontSize: "0.85rem" }}>{list.data.count} file{list.data.count === 1 ? "" : "s"}{sort.key === "name" ? ", in AVL order" : ""}</span>}
          </div>
          <ErrorNote error={list.error} />
          <div className="panel" style={{ overflowX: "auto" }}>
            {list.data && list.data.files.length === 0 ? (
              <div className="empty">{type === "All" ? "No files yet. Upload one or drop it above." : `No ${type.toLowerCase()} files.`}</div>
            ) : (
              <table className="files">
                <thead><tr>{COLUMNS.map((c) => <th key={c.key} className={`${c.cls || ""} ${c.num ? "num" : ""}`} aria-sort={sort.key === c.key ? (sort.order === "asc" ? "ascending" : "descending") : undefined}>{header(c)}</th>)}</tr></thead>
                <tbody>
                  {(list.data?.files || []).map((f) => (
                    <tr key={f.file_id} aria-selected={selected === f.file_id} tabIndex={0}
                      onClick={() => setSelected(f.file_id)} onKeyDown={(e) => e.key === "Enter" && setSelected(f.file_id)}>
                      <td><div className="fname"><FileBadge file={f} /><span>{f.filename}</span></div></td>
                      <td className="hide-sm hide-detail muted">{f.file_type}</td>
                      <td className="num">{f.formatted_size}</td>
                      <td><Priority value={f.priority} /></td>
                      <td className="num hide-sm">{f.current_version}</td>
                      <td className="hide-sm hide-detail muted">{fmtDate(f.upload_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
        {selected && <FilePanel key={selected} fileId={selected} onClose={() => setSelected(null)} onSelect={setSelected} />}
      </div>
    </>
  );
}
