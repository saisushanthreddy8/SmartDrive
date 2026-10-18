// Minimal inline icon set (stroke icons, inherit currentColor).
const P = { width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
export const Search = () => <svg {...P}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>;
export const Upload = () => <svg {...P}><path d="M12 15V3m0 0L7 8m5-5 5 5" /><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></svg>;
export const Download = () => <svg {...P}><path d="M12 3v12m0 0-5-5m5 5 5-5" /><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></svg>;
export const Trash = () => <svg {...P}><path d="M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3" /></svg>;
export const Close = () => <svg {...P}><path d="M6 6l12 12M18 6 6 18" /></svg>;
export const Plus = () => <svg {...P}><path d="M12 5v14M5 12h14" /></svg>;
export const Refresh = () => <svg {...P}><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" /></svg>;
export const Play = () => <svg {...P}><path d="M7 4v16l13-8z" /></svg>;
export const Shield = () => <svg {...P}><path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></svg>;
export const Back = () => <svg {...P}><path d="m15 18-6-6 6-6" /></svg>;
export const Next = () => <svg {...P}><path d="m9 18 6-6-6-6" /></svg>;
export const Logo = () => (
  <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
    <rect width="32" height="32" rx="8" fill="var(--chrome-2)" />
    <path d="M16 12 9 19M16 12l7 7" stroke="var(--chrome-ink)" strokeWidth="1.6" />
    <circle cx="16" cy="9" r="3.2" fill="var(--avl)" /><circle cx="9" cy="22" r="3.2" fill="var(--trie)" /><circle cx="23" cy="22" r="3.2" fill="var(--heap)" />
  </svg>
);
