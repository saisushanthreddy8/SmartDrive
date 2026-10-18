// SVG tree layouts used by the Algorithm Explorer.
//  - Binary trees (AVL, Heap, Merkle) use in-order x positions, so a BST reads left-to-right sorted.
//  - N-ary trees (Trie) use leaf-count layout: each leaf gets a column, parents sit over their children.

export function layoutBinary(root, kids = (n) => [n.left, n.right]) {
  const nodes = [], edges = [];
  let col = 0, maxDepth = 0;
  const walk = (n, depth, parent) => {
    if (!n) return;
    const [l, r] = kids(n);
    const me = { data: n, depth, id: nodes.length };
    nodes.push(me);
    if (parent) edges.push([parent, me]);
    walk(l, depth + 1, me);
    me.col = col++;
    walk(r, depth + 1, me);
    maxDepth = Math.max(maxDepth, depth);
  };
  walk(root, 0, null);
  return { nodes, edges, cols: col, depth: maxDepth };
}

export function layoutNary(root, kids = (n) => n.children || []) {
  const nodes = [], edges = [];
  let leaf = 0, maxDepth = 0;
  const walk = (n, depth, parent) => {
    const me = { data: n, depth, id: nodes.length };
    nodes.push(me);
    if (parent) edges.push([parent, me]);
    const ch = kids(n);
    if (!ch.length) me.col = leaf++;
    else {
      const placed = ch.map((c) => walk(c, depth + 1, me));
      me.col = (placed[0].col + placed[placed.length - 1].col) / 2;
    }
    maxDepth = Math.max(maxDepth, depth);
    return me;
  };
  if (root) walk(root, 0, null);
  return { nodes, edges, cols: Math.max(leaf, 1), depth: maxDepth };
}

/**
 * Generic renderer. `node(n, x, y)` returns the SVG for one node; `hotEdge(a, b)` highlights an edge.
 */
export function TreeSvg({ layout, colW = 64, rowH = 70, pad = 30, node, hotEdge, hue, label }) {
  const { nodes, edges, cols, depth } = layout;
  if (!nodes.length) return <div className="empty">Nothing to draw yet.</div>;
  const w = Math.max(cols, 1) * colW + pad * 2;
  const h = (depth + 1) * rowH + pad * 2 - rowH / 2;
  const X = (n) => pad + n.col * colW + colW / 2;
  const Y = (n) => pad + n.depth * rowH;
  return (
    <div className="diagram" style={{ "--hue": hue }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ maxWidth: w, minWidth: Math.min(w, Math.max(520, w * 0.6)), height: "auto" }} role="img" aria-label={label}>
        {edges.map(([a, b], i) => (
          <line key={i} className={`edge ${hotEdge?.(a, b) ? "hot" : ""}`} x1={X(a)} y1={Y(a)} x2={X(b)} y2={Y(b)} />
        ))}
        {nodes.map((n) => <g key={n.id}>{node(n, X(n), Y(n))}</g>)}
      </svg>
    </div>
  );
}

export function heapToTree(arr) {
  const build = (i) => (i < arr.length ? { ...arr[i], left: build(2 * i + 1), right: build(2 * i + 2) } : null);
  return build(0);
}
