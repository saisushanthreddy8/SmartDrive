// Dynamic-programming table with the backtracked path highlighted.
export default function DPTable({ rows, cols, table, path = [], match, hue, caption }) {
  const onPath = new Set(path.map(([i, j]) => `${i},${j}`));
  return (
    <div className="dp-wrap" style={{ "--hue": hue }}>
      <table className="dp">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            <th className="rowh"></th>
            {cols.map((c, j) => <th key={j} scope="col" title={String(c)}>{String(c).slice(0, 4)}</th>)}
          </tr>
        </thead>
        <tbody>
          {table.map((row, i) => (
            <tr key={i}>
              <th className="rowh" scope="row" title={String(rows[i])}>{String(rows[i])}</th>
              {row.map((v, j) => {
                const k = `${i},${j}`;
                return <td key={j} className={`${onPath.has(k) ? "path" : ""} ${match?.(i, j) ? "match" : ""}`}>{v}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
