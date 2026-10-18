import { useEffect, useState } from "react";
import { api, fmtBytes, fmtMs, trace } from "../api.js";
import { DSLabel, ErrorNote, FileBadge, Meter, useLive, PageUses } from "../components/Common.jsx";

const METHOD_NOTES = {
  "Dynamic Programming": "Fills a table of best values for every item and capacity. Always optimal; cost grows with the budget.",
  "Greedy (Ratio)": "Takes files in order of priority per KB. Very fast, but can leave space unused and miss the best set.",
  "Branch & Bound": "Explores include/exclude choices best-first and prunes branches that cannot beat the best so far. Optimal.",
};

export default function OptimizerPage({ openFile }) {
  const files = useLive(() => api.files());
  const [kb, setKb] = useState(7);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const run = async (value = kb) => {
    setErr(null);
    try {
      const r = await api.optimize(Number(value));
      setRes(r);
      r.results.forEach((x) => trace("knap", `${x.method}: value ${x.total_value}, ${x.nodes_explored.toLocaleString()} steps`, x.time_ms));
    } catch (e) { setErr(e); }
  };
  useEffect(() => { run(); }, []);
  const totalKb = Math.ceil((files.data?.files || []).reduce((s, f) => s + f.file_size, 0) / 1024);
  const best = res ? Math.max(...res.results.map((r) => r.total_value)) : 0;
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["knap", "heap"]} />
          <h1>Storage optimizer</h1>
          <p>If you could keep only a fixed amount of storage, which files should stay? This is the 0/1 knapsack problem: size is the weight, priority is the value. Three algorithms solve it below.</p>
        </div>
      </div>
      <section className="panel panel-pad" style={{ marginBottom: 18 }}>
        <form className="row" onSubmit={(e) => { e.preventDefault(); run(); }}>
          <label className="field grow" style={{ minWidth: 240 }}>
            Storage budget: {kb} KB of {totalKb} KB used today
            <input type="range" min={0} max={Math.max(totalKb, 1)} value={Math.min(kb, Math.max(totalKb, 1))} onChange={(e) => setKb(Number(e.target.value))} onMouseUp={(e) => run(e.target.value)} onKeyUp={(e) => run(e.target.value)} style={{ accentColor: "var(--knap)" }} />
          </label>
          <input className="input" type="number" min={0} step="any" value={kb} onChange={(e) => setKb(e.target.value)} style={{ width: 110 }} aria-label="Budget in KB" />
          <button className="btn primary">Solve</button>
        </form>
      </section>
      <ErrorNote error={err} />
      {res && (
        <>
          <section className="panel" style={{ marginBottom: 18, overflowX: "auto" }}>
            <div className="panel-head"><DSLabel ds="knap">Comparison</DSLabel><span className="muted" style={{ fontSize: "0.85rem" }}>Budget {fmtBytes(res.capacity_bytes)}</span></div>
            <table className="data">
              <thead><tr><th>Method</th><th className="num">Total priority</th><th>Space used</th><th className="num">Steps</th><th className="num">Time</th><th>Optimal</th></tr></thead>
              <tbody>
                {res.results.map((r) => (
                  <tr key={r.method} className={r.total_value === best ? "best" : ""}>
                    <td><b>{r.method}</b><div className="muted" style={{ fontSize: "0.82rem", maxWidth: 46 + "ch" }}>{METHOD_NOTES[r.method]}</div></td>
                    <td className="num" style={{ fontSize: "1.1rem" }}>{r.total_value}</td>
                    <td style={{ minWidth: 150 }}><Meter pct={r.utilization_pct} hue="var(--knap)" /><span className="muted" style={{ fontSize: "0.82rem" }}>{r.utilization_pct}%</span></td>
                    <td className="num">{r.nodes_explored.toLocaleString()}{r.nodes_pruned ? <div className="muted" style={{ fontSize: "0.8rem" }}>{r.nodes_pruned} pruned</div> : null}</td>
                    <td className="num mono">{fmtMs(r.time_ms)}</td>
                    <td>{r.is_optimal ? <span style={{ color: "var(--ok)" }}>Yes</span> : <span style={{ color: "var(--danger)" }}>No, {best - r.total_value} less</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="panel" style={{ overflowX: "auto" }}>
            <div className="panel-head"><DSLabel ds="knap">Which files each method keeps</DSLabel></div>
            <table className="data">
              <thead><tr><th>File</th><th className="num">Size</th><th className="num">Priority</th>{res.results.map((r) => <th key={r.method}>{r.method.replace(" (Ratio)", "")}</th>)}</tr></thead>
              <tbody>
                {(files.data?.files || []).map((f) => (
                  <tr key={f.file_id}>
                    <td><button className="linkish btn ghost small" onClick={() => openFile(f.file_id)}><span className="fname"><FileBadge file={f} /><span>{f.filename}</span></span></button></td>
                    <td className="num">{f.formatted_size}</td>
                    <td className="num">{f.priority}</td>
                    {res.results.map((r) => {
                      const keep = r.selected_files.some((s) => s.file_id === f.file_id);
                      return <td key={r.method} style={{ color: keep ? "var(--ok)" : "var(--muted)" }}>{keep ? "Keep" : "Skip"}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}
