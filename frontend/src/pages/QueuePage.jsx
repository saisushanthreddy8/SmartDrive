import { useState } from "react";
import { api, changed, toast, trace } from "../api.js";
import { DSLabel, ErrorNote, FileBadge, Priority, useLive, PageUses } from "../components/Common.jsx";
import { heapToTree, layoutBinary, TreeSvg } from "../components/Trees.jsx";
import { Play, Refresh } from "../components/Icons.jsx";

export function HeapDiagram({ nodes, hotIndex = 0, labelOf = (n) => n.label }) {
  const root = heapToTree(nodes);
  return (
    <TreeSvg layout={layoutBinary(root)} hue="var(--heap)" colW={50} rowH={74} label="Max heap as a binary tree"
      node={(n, x, y) => (
        <>
          <circle className={`node ${n.data.index === hotIndex ? "hot" : ""}`} cx={x} cy={y} r={17} />
          <text x={x} y={y + 4} textAnchor="middle" className={n.data.index === hotIndex ? "on-hot" : ""}>{n.data.priority}</text>
          <text x={x} y={y + 31} textAnchor="middle" className="small">{String(labelOf(n.data)).slice(0, 12)}</text>
          <text x={x - 22} y={y - 14} textAnchor="end" className="small">[{n.data.index}]</text>
        </>
      )} />
  );
}

export default function QueuePage({ openFile }) {
  const q = useLive(() => api.queue());
  const [last, setLast] = useState(null);
  const next = async () => {
    try {
      const r = await api.queueNext();
      setLast(r);
      trace("heap", `extract_max -> "${r.processed.filename}" (priority ${r.priority}), sift down`);
      q.reload();
    } catch (e) { toast(e.message, true); }
  };
  const reset = async () => {
    try { const r = await api.queueReset(); trace("heap", `build-heap from ${r.size} files in O(n)`); toast("Queue rebuilt with every file"); q.reload(); changed(); }
    catch (e) { toast(e.message, true); }
  };
  const data = q.data;
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["heap"]} />
          <h1>Priority queue</h1>
          <p>Files waiting to be processed, highest priority first. The array below is the heap itself: index i has children 2i+1 and 2i+2, and the root is always the largest.</p>
        </div>
        <div className="row">
          <button className="btn primary" onClick={next} disabled={!data?.queue.length}><Play /> Process next</button>
          <button className="btn" onClick={reset}><Refresh /> Refill queue</button>
        </div>
      </div>
      <ErrorNote error={q.error} />
      {last && <div className="note ok" style={{ marginBottom: 16 }}>Processed <b>{last.processed.filename}</b> at priority {last.priority}. {last.remaining} left in the heap.</div>}
      {data && (
        <div className="grid-2">
          <section className="panel">
            <div className="panel-head"><DSLabel ds="heap">Processing order</DSLabel><span className="muted">{data.queue.length} waiting</span></div>
            {data.queue.length === 0 ? <div className="empty">The queue is empty. Refill it to load every file again.</div> : (
              <ol className="results" style={{ listStyle: "none" }}>
                {data.queue.map((it, i) => (
                  <li key={it.file.file_id} style={{ gridTemplateColumns: "28px 1fr auto", alignItems: "center", display: "grid" }}>
                    <span className="mono muted">{i + 1}</span>
                    <button className="linkish" onClick={() => openFile(it.file.file_id)}><span className="fname"><FileBadge file={it.file} /><span>{it.file.filename}</span></span></button>
                    <Priority value={it.priority} />
                  </li>
                ))}
              </ol>
            )}
          </section>
          <section className="panel">
            <div className="panel-head"><DSLabel ds="heap">Heap as a tree</DSLabel><span className="muted">root = next to process</span></div>
            <div className="panel-pad">{data.heap.length ? <HeapDiagram nodes={data.heap} /> : <div className="empty">Empty heap.</div>}</div>
            {data.heap.length > 0 && (
              <div className="panel-pad" style={{ paddingTop: 0 }}>
                <div className="muted" style={{ fontSize: "0.82rem", marginBottom: 6 }}>Underlying array</div>
                <div className="chips mono">{data.heap.map((n) => <span key={n.index} className="tag" title={n.label}>[{n.index}] {n.priority}</span>)}</div>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
