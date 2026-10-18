import { useEffect, useState } from "react";
import { DS, fmtMs, onFilesChanged, onToast, onTrace } from "../api.js";

const TYPE_COLORS = { Document: "#3d6fb6", Image: "#2e8a6e", Video: "#8b4fc2", Audio: "#c0576e", Archive: "#8a6d3b", Other: "#6b7785" };

export function FileBadge({ file }) {
  const ext = (file.file_extension || "").replace(".", "").slice(0, 4) || "file";
  return <span className="ftype" style={{ background: TYPE_COLORS[file.file_type] || TYPE_COLORS.Other }} aria-hidden="true">{ext}</span>;
}

export function DSLabel({ ds, children }) {
  const d = DS[ds];
  return <span className="ds" style={{ "--hue": d.hue }}>{children ?? d.name}</span>;
}

/** Row of coloured labels naming the data structures a page is built on. */
export function PageUses({ ds }) {
  return <div className="page-uses">{ds.map((d) => <DSLabel key={d} ds={d} />)}</div>;
}

export function Priority({ value }) {
  return (
    <span className="prio" title={`Priority ${value} of 10`}>
      <span className="prio-bar"><i style={{ width: `${value * 10}%` }} /></span>
      <span className="num">{value}</span>
    </span>
  );
}

export function Meter({ pct, hue }) {
  return <div className="meter" style={{ "--hue": hue }} role="meter" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${Math.min(100, pct)}%` }} /></div>;
}

export function Took({ ms }) {
  return ms == null ? null : <span className="mono muted">{fmtMs(ms)}</span>;
}

export function TraceStrip() {
  const [items, setItems] = useState([]);
  useEffect(() => onTrace((e) => setItems((xs) => [e, ...xs].slice(0, 60))), []);
  return (
    <section className="trace" aria-label="Operation trace">
      <div className="trace-head">
        <span>Trace: which data structure handled each action</span>
        {items.length > 0 && <button onClick={() => setItems([])}>Clear</button>}
      </div>
      <ol aria-live="polite">
        {items.length === 0 && <li style={{ display: "block", color: "var(--muted)" }}>Search, upload or open a file to see the structures at work.</li>}
        {items.map((e) => (
          <li key={e.id} style={{ "--hue": DS[e.ds]?.hue }}>
            <span className="t-time">{e.at.toLocaleTimeString([], { hour12: false })}</span>
            <span className="t-ds">{DS[e.ds]?.name}</span>
            <span>{e.text}</span>
            <span className="t-ms">{e.ms != null ? fmtMs(e.ms) : DS[e.ds]?.cost}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function Toasts() {
  const [items, setItems] = useState([]);
  useEffect(() => onToast((t) => {
    setItems((xs) => [...xs, t]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== t.id)), t.bad ? 6000 : 3200);
  }), []);
  return <div className="toasts" role="status">{items.map((t) => <div key={t.id} className={`toast ${t.bad ? "bad" : ""}`}>{t.text}</div>)}</div>;
}

export function useAsync(fn, deps) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  const reload = () => {
    set((s) => ({ ...s, loading: true }));
    return fn().then((data) => set({ data, error: null, loading: false }), (error) => set({ data: null, error, loading: false }));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, deps);
  return { ...state, reload };
}

/** Like useAsync, but also reloads whenever files change anywhere in the app (upload, edit, delete...). */
export function useLive(fn, deps = []) {
  const state = useAsync(fn, deps);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => onFilesChanged(state.reload), deps);
  return state;
}

export function ErrorNote({ error }) {
  return error ? <div className="note bad">{error.message}</div> : null;
}
