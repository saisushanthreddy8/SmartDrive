import { useEffect, useState } from "react";
import { api, changed, short, toast, trace } from "../api.js";
import { DSLabel, ErrorNote, Took, useLive, PageUses } from "../components/Common.jsx";
import { layoutBinary, TreeSvg } from "../components/Trees.jsx";
import { Shield } from "../components/Icons.jsx";

export function MerkleDiagram({ root, bad = new Set(), hotPath = new Set() }) {
  // Pad duplicates (odd leaf copied up) share a file_id; mark them so the diagram stays honest.
  return (
    <TreeSvg layout={layoutBinary(root)} hue="var(--merkle)" colW={60} rowH={66} label="Merkle tree of file hashes"
      hotEdge={(a, b) => hotPath.has(a.data.hash) && hotPath.has(b.data.hash)}
      node={(n, x, y) => {
        const d = n.data;
        const isBad = d.leaf && bad.has(d.file_id);
        const hot = hotPath.has(d.hash);
        return (
          <>
            <rect className={`node ${isBad ? "bad" : hot ? "hot" : d.leaf ? "end" : ""}`} x={x - 46} y={y - 13} width={92} height={26} rx={5} />
            <text x={x} y={y + 4} textAnchor="middle" className={hot && !isBad ? "on-hot" : ""}>{d.hash.slice(0, 10)}</text>
            {d.leaf && <text x={x} y={y + 27} textAnchor="middle" className="small">{(d.filename || "").slice(0, 15)}</text>}
          </>
        );
      }} />
  );
}

export default function IntegrityPage({ openFile }) {
  const tree = useLive(() => api.explorer("merkle"));
  const [audit, setAudit] = useState(null);
  const [err, setErr] = useState(null);
  const run = async () => {
    setErr(null);
    try {
      const r = await api.audit();
      setAudit(r);
      trace("merkle", `audit ${r.total_files} files against the tree: ${r.tampered_count} problem${r.tampered_count === 1 ? "" : "s"}`, r.took_ms);
    } catch (e) { setErr(e); }
  };
  useEffect(() => { run(); }, []);
  const repair = async (v) => {
    try { await api.repair(v.file_id); trace("disk", `restored "${v.filename}" from its latest snapshot`); toast(`Repaired ${v.filename}`); run(); changed(); }
    catch (e) { toast(e.message, true); }
  };
  const bad = new Set((audit?.violations || []).map((v) => v.file_id));
  return (
    <>
      <div className="page-head">
        <div>
          <PageUses ds={["merkle"]} />
          <h1>Integrity</h1>
          <p>Each file’s SHA-256 hash is a leaf. Parents hash their two children, so changing one byte of one file changes the root. An audit re-hashes every file on disk and compares.</p>
        </div>
        <button className="btn primary" onClick={run}><Shield /> Audit all files</button>
      </div>
      <ErrorNote error={err || tree.error} />
      {audit && (
        <div className={`note ${audit.is_tampered ? "bad" : "ok"}`} style={{ marginBottom: 16 }}>
          {audit.is_tampered
            ? `${audit.tampered_count} of ${audit.total_files} files no longer match their recorded hash.`
            : `All ${audit.total_files} files match their recorded hashes.`} <Took ms={audit.took_ms} />
        </div>
      )}
      {audit?.violations.length > 0 && (
        <section className="panel" style={{ marginBottom: 18 }}>
          <div className="panel-head"><DSLabel ds="merkle">Problems found</DSLabel></div>
          <table className="data">
            <thead><tr><th>File</th><th>Status</th><th className="hide-sm">Expected</th><th className="hide-sm">On disk</th><th></th></tr></thead>
            <tbody>
              {audit.violations.map((v) => (
                <tr key={v.file_id}>
                  <td><button className="linkish btn ghost small" onClick={() => openFile(v.file_id)}>{v.filename}</button></td>
                  <td style={{ color: "var(--danger)" }}>{v.status === "MISSING" ? "Missing from disk" : "Content changed"}</td>
                  <td className="hash hide-sm">{short(v.expected_hash, 12)}</td>
                  <td className="hash hide-sm">{v.status === "MISSING" ? "—" : short(v.actual_hash, 12)}</td>
                  <td><button className="btn small" onClick={() => repair(v)}>Repair</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section className="panel">
        <div className="panel-head">
          <DSLabel ds="merkle">Merkle tree</DSLabel>
          {tree.data?.root_hash && <span className="muted" style={{ fontSize: "0.85rem" }}>root <span className="mono">{short(tree.data.root_hash, 16)}</span></span>}
        </div>
        <div className="panel-pad">
          {tree.data?.root ? <MerkleDiagram root={tree.data.root} bad={bad} /> : <div className="empty">Upload a file to build the tree.</div>}
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: 10 }}>Leaves are sorted by filename. With an odd count, the last node is paired with a copy of itself. Red leaves failed the latest audit.</p>
        </div>
      </section>
    </>
  );
}
