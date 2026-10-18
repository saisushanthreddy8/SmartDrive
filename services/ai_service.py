"""
SmartDrive - Offline AI Assistant
Runs locally (no API key, no internet), built from classic information-retrieval algorithms:
    - Text extraction: txt/code/csv/md, docx/pptx/xlsx (zip of XML), pdf (optional pypdf)
    - TF-IDF vectors + inverted index + cosine similarity -> content search, similar files, Q&A
    - Extractive summary, keywords, rule-based tags, explainable priority suggestion
    - Duplicates: identical SHA-256, near-identical text, similar names (edit distance)
"""
import math, re, zipfile, io, logging
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any, Set
from models.file_model import FileModel
from data_structures.edit_distance import EditDistance

logging.getLogger("pypdf").setLevel(logging.ERROR)  # Hide parser warnings on malformed PDFs
MAX_TEXT_CHARS = 200_000
TEXT_EXTS = {".txt", ".md", ".csv", ".tsv", ".json", ".log", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp",
             ".h", ".cs", ".go", ".rs", ".rb", ".php", ".html", ".htm", ".css", ".xml", ".yml", ".yaml", ".ini", ".sql", ".tex", ".m", ".r"}

STOPWORDS = set("""a about above after again against all am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself
his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves
out over own same she should so some such than that the their theirs them themselves then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your yours yourself yourselves
also may might must shall us via per etc using use used one two three new get got like line sample content demo""".split())

TAG_WORDS: Dict[str, Set[str]] = {
    "Academic": {"assignment", "exam", "lecture", "semester", "course", "notes", "syllabus", "homework", "quiz", "university",
                 "college", "student", "professor", "review", "lab", "grade", "marks", "thesis", "adsa"},
    "Machine Learning": {"machine", "learning", "model", "neural", "dataset", "training", "regression", "classification",
                         "supervised", "unsupervised", "accuracy", "cnn", "deep", "feature", "prediction", "ai"},
    "Finance": {"invoice", "budget", "payment", "salary", "expense", "tax", "bank", "price", "cost", "revenue", "bill", "receipt"},
    "Project": {"project", "architecture", "design", "requirement", "milestone", "sprint", "roadmap", "phase", "system",
                "module", "implementation", "diagram"},
    "Meeting": {"meeting", "minutes", "agenda", "discussion", "attendees", "action", "items", "call"},
    "Code": {"def", "class", "function", "import", "return", "const", "var", "public", "static", "void", "algorithm", "code"},
    "Report": {"report", "summary", "analysis", "results", "conclusion", "findings", "evaluation", "abstract", "final"},
    "Data": {"data", "database", "sql", "table", "query", "backup", "csv", "records", "schema"},
    "Presentation": {"slides", "presentation", "deck", "pitch", "talk"},
    "Media": {"audio", "video", "recording", "photo", "image", "music", "podcast"},
}
URGENCY_WORDS = {"urgent": 2, "deadline": 2, "asap": 2, "critical": 2, "important": 1, "final": 1, "exam": 1, "due": 1,
                 "submission": 1, "submit": 1, "review": 1, "assignment": 1, "report": 1}
TYPE_BASE_PRIORITY = {"Document": 5, "Image": 4, "Video": 3, "Audio": 3, "Archive": 2, "Other": 3}
SUFFIXES = ("ations", "ation", "ings", "ing", "ions", "ion", "ers", "ed", "es", "s")

# --- Text Processing ---
def words(text: str) -> List[str]:
    """Lowercase words, without stopwords."""
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower()) if w not in STOPWORDS]

def stem(w: str) -> str:
    """Light suffix stripping so "insertion", "inserting" and "inserts" all become "insert"."""
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4 and not (suf == "s" and w.endswith("ss")):
            return w[:-len(suf)]
    return w

def tokenize(text: str) -> List[str]:
    return [stem(w) for w in words(text)]

def surface_forms(text: str) -> Dict[str, str]:
    """For each stem, its most common spelling in the text (so 'submiss' is shown as 'submission')."""
    seen: Dict[str, Counter] = {}
    for w in words(text): seen.setdefault(stem(w), Counter())[w] += 1
    return {st: c.most_common(1)[0][0] for st, c in seen.items()}

def split_sentences(text: str) -> List[str]:
    """Sentences and lines of at least 12 characters, without repeats."""
    parts = (p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text))
    return list(dict.fromkeys(p for p in parts if len(p) >= 12))

def extract_text(filename: str, data: bytes) -> str:
    """Best-effort plain text from a file's bytes; '' for formats it cannot read (images, audio...)."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext in TEXT_EXTS:
            return data[:MAX_TEXT_CHARS].decode("utf-8", "replace")
        if ext in (".docx", ".pptx", ".xlsx") and zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as z:  # Office files are zips of XML
                if ext == ".docx": parts = ["word/document.xml"]
                elif ext == ".xlsx": parts = ["xl/sharedStrings.xml"]
                else: parts = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                     key=lambda n: int(re.findall(r"\d+", n)[0]))
                xml = " \n".join(z.read(p).decode("utf-8", "ignore") for p in parts if p in z.namelist())
                return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml)).strip()[:MAX_TEXT_CHARS]
        if data.startswith(b"%PDF"):
            from pypdf import PdfReader  # Optional dependency
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages[:50])[:MAX_TEXT_CHARS]
        return data[:MAX_TEXT_CHARS].decode("utf-8")  # Plain text saved with another extension (e.g. demo files)
    except Exception:
        return ""

# --- TF-IDF Index ---
class TFIDFIndex:
    def __init__(self):
        self.docs: Dict[str, Counter] = {}           # doc id -> term counts
        self.inverted: Dict[str, Set[str]] = {}      # term -> doc ids that contain it
        self.idf: Dict[str, float] = {}
        self.vectors: Dict[str, Dict[str, float]] = {}

    def build(self, docs: Dict[str, List[str]]) -> None:
        self.docs = {d: Counter(toks) for d, toks in docs.items()}
        self.inverted = {}
        for d, counts in self.docs.items():
            for term in counts: self.inverted.setdefault(term, set()).add(d)
        n = len(self.docs)
        self.idf = {t: math.log((1 + n) / (1 + len(ds))) + 1 for t, ds in self.inverted.items()}  # Rare terms weigh more
        self.vectors = {d: self._vector(counts) for d, counts in self.docs.items()}

    def _vector(self, counts: Counter) -> Dict[str, float]:
        """Unit-length vector of (1 + log tf) * idf."""
        vec = {t: (1 + math.log(c)) * self.idf[t] for t, c in counts.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def vectorize(self, tokens: List[str]) -> Dict[str, float]: return self._vector(Counter(tokens))

    @staticmethod
    def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if len(a) > len(b): a, b = b, a
        return sum(v * b.get(t, 0.0) for t, v in a.items())

    def search(self, tokens: List[str], limit: int = 10) -> List[Tuple[str, float]]:
        """Only documents sharing at least one term with the query are scored (inverted index)."""
        query = self.vectorize(tokens)
        candidates = set().union(*(self.inverted[t] for t in query)) if query else set()
        scored = [(d, self.cosine(query, self.vectors[d])) for d in candidates]
        return sorted((s for s in scored if s[1] > 0), key=lambda s: -s[1])[:limit]

    def top_terms(self, doc_id: str, k: int = 8) -> List[Tuple[str, float]]:
        return sorted(self.vectors.get(doc_id, {}).items(), key=lambda x: -x[1])[:k]

# --- AI Service ---
class AIService:
    NEAR_DUP_THRESHOLD = 0.85

    def __init__(self, engine):
        self.engine = engine
        self.index = TFIDFIndex()
        self._text_cache: Dict[Tuple[str, str], str] = {}  # (file_id, sha256) -> extracted text
        self._fingerprint: Optional[Tuple] = None

    def _files(self) -> List[FileModel]: return [f for _, f in self.engine.list_all_files_sorted()]

    def get_text(self, f: FileModel) -> str:
        key = (f.file_id, f.sha256_hash)
        if key not in self._text_cache:
            try: data = self.engine.storage.read_file_content(f.storage_path) if self.engine.storage else b""
            except (FileNotFoundError, ValueError): data = b""
            self._text_cache[key] = extract_text(f.filename, data)
        return self._text_cache[key]

    def _meta_text(self, f: FileModel) -> str:
        return " ".join([re.sub(r"[_\-.]", " ", f.filename.rsplit(".", 1)[0]), f.description or "", " ".join(f.tags)])

    def _doc_tokens(self, f: FileModel) -> List[str]:
        name = tokenize(re.sub(r"[_\-.]", " ", f.filename.rsplit(".", 1)[0]))
        meta = tokenize(" ".join([f.description or "", " ".join(f.tags)]))
        return name * 3 + meta * 2 + tokenize(self.get_text(f))  # Filename and metadata count more

    def refresh(self) -> None:
        """Rebuilds the index only when a file, its content or its metadata changed."""
        files = self._files()
        fingerprint = tuple((f.file_id, f.sha256_hash, f.description, tuple(f.tags)) for f in files)
        if fingerprint == self._fingerprint: return
        live = {(f.file_id, f.sha256_hash) for f in files}
        self._text_cache = {k: v for k, v in self._text_cache.items() if k in live}
        self.index.build({f.file_id: self._doc_tokens(f) for f in files})
        self._fingerprint = fingerprint

    def _rank_sentences(self, f: FileModel, query: List[str], doc_score: float = 0.0) -> List[Tuple[float, str]]:
        """
        Scores each sentence of a file against the query: similarity, share of question words it contains,
        and how good the whole file matched. Very short lines and titles are down-weighted.
        """
        qv, q_terms, ranked = self.index.vectorize(query), set(query), []
        for sent in split_sentences(self.get_text(f))[:400]:
            toks = tokenize(sent)
            sim = self.index.cosine(qv, self.index.vectorize(toks))
            if sim <= 0: continue
            coverage = len(q_terms & set(toks)) / len(q_terms)
            weight = min(1.0, len(toks) / 4)
            if not sent.endswith((".", "!", "?")) and len(toks) < 10: weight *= 0.75  # Probably a heading
            ranked.append(((0.5 * sim + 0.2 * doc_score + 0.3 * coverage) * weight, sent))
        return sorted(ranked, key=lambda r: -r[0])

    # --- Search & Q&A ---
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        self.refresh()
        toks, forms = tokenize(query), surface_forms(query)
        results = []
        for fid, score in self.index.search(toks, limit):
            f = self.engine.get_file_by_id(fid)
            best = self._rank_sentences(f, toks)
            results.append({"file": f, "score": round(score, 4),
                            "matched_terms": sorted(forms.get(t, t) for t in set(toks) if t in self.index.docs[fid]),
                            "snippet": best[0][1][:240] if best else None})
        return results

    def ask(self, question: str, limit: int = 3) -> Dict[str, Any]:
        """Extractive Q&A: the best sentences from the best-matching files."""
        self.refresh()
        toks = tokenize(question)
        passages = []
        for fid, doc_score in self.index.search(toks, 5):
            f = self.engine.get_file_by_id(fid)
            passages += [{"file": f, "text": sent[:300], "score": round(score, 4)}
                         for score, sent in self._rank_sentences(f, toks, doc_score)]
        answers = sorted(passages, key=lambda p: -p["score"])[:limit]
        forms = surface_forms(question)
        return {"question": question, "terms": sorted({forms.get(t, t) for t in toks}), "answers": answers,
                "found": bool(answers), "note": None if answers else "No matching content found in your files."}

    # --- Per-file Insights ---
    def summarize(self, f: FileModel, n: int = 3) -> List[str]:
        """Picks the n sentences with the rarest (most informative) words, kept in original order."""
        self.refresh()
        sents = split_sentences(self.get_text(f))[:600]
        if len(sents) <= n: return sents
        def informativeness(s: str) -> float:
            terms = set(tokenize(s))
            return sum(self.index.idf.get(t, 0) for t in terms) / math.sqrt(len(terms)) if terms else 0
        best = sorted(range(len(sents)), key=lambda i: -informativeness(sents[i]))[:n]
        return [sents[i][:300] for i in sorted(best)]

    def keywords(self, f: FileModel, k: int = 8) -> List[Dict[str, Any]]:
        self.refresh()
        forms = surface_forms(self._meta_text(f) + " " + self.get_text(f))
        return [{"term": forms.get(t, t), "weight": round(w, 4)} for t, w in self.index.top_terms(f.file_id, k)]

    def _word_set(self, f: FileModel) -> Set[str]:
        return set(words(self._meta_text(f) + " " + self.get_text(f)))

    def suggest_tags(self, f: FileModel) -> List[Dict[str, Any]]:
        """A tag is suggested when 2+ of its words appear, or one appears in the filename."""
        found, name_words = self._word_set(f), set(words(self._meta_text(f)))
        tags = []
        for tag, tag_words in TAG_WORDS.items():
            hits = sorted(tag_words & found)
            if len(hits) >= 2 or tag_words & name_words:
                tags.append({"tag": tag, "evidence": hits[:5], "score": len(hits)})
        tags.sort(key=lambda t: -t["score"])
        if f.file_type != "Other" and f.file_type not in [t["tag"] for t in tags]:
            tags.append({"tag": f.file_type, "evidence": [f.file_extension], "score": 0})
        return tags[:5]

    def suggest_priority(self, f: FileModel) -> Dict[str, Any]:
        """Explainable score: type baseline + urgency words + recency + edit activity - very large size."""
        base = TYPE_BASE_PRIORITY.get(f.file_type, 3)
        score, reasons = base, [f"{f.file_type} baseline: {base}"]
        urgent = [w for w in URGENCY_WORDS if w in self._word_set(f)]
        if urgent:
            bonus = min(3, sum(URGENCY_WORDS[w] for w in urgent))
            score += bonus
            reasons.append(f"Urgency words ({', '.join(urgent)}): +{bonus}")
        uploaded = f.upload_date if f.upload_date.tzinfo else f.upload_date.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - uploaded).days
        if age_days <= 7:
            score += 1
            reasons.append("Uploaded in the last 7 days: +1")
        elif age_days > 90:
            score -= 1
            reasons.append("Older than 90 days: -1")
        if f.current_version >= 3:
            score += 1
            reasons.append(f"Actively edited ({f.current_version} versions): +1")
        if f.file_size > 50 * 1024 * 1024:
            score -= 1
            reasons.append("Very large file: -1")
        return {"suggested": max(1, min(10, score)), "current": f.priority, "reasons": reasons}

    def similar_files(self, f: FileModel, k: int = 3) -> List[Dict[str, Any]]:
        self.refresh()
        mine = self.index.vectors.get(f.file_id, {})
        scored = [(o, self.index.cosine(mine, self.index.vectors.get(o.file_id, {}))) for o in self._files() if o.file_id != f.file_id]
        return [{"file": o, "score": round(s, 4)} for o, s in sorted(scored, key=lambda x: -x[1])[:k] if s > 0.05]

    def insights(self, f: FileModel) -> Dict[str, Any]:
        text = self.get_text(f)
        word_count = len(re.findall(r"\w+", text))
        return {
            "has_text": bool(text.strip()),
            "stats": {"words": word_count, "lines": text.count("\n") + 1 if text else 0, "characters": len(text),
                      "reading_minutes": round(word_count / 200, 1)},
            "summary": self.summarize(f), "keywords": self.keywords(f), "tags": self.suggest_tags(f),
            "priority": self.suggest_priority(f), "similar": self.similar_files(f),
        }

    # --- Duplicate Detection ---
    def find_duplicates(self) -> Dict[str, Any]:
        self.refresh()
        files = self._files()
        by_hash: Dict[str, List[FileModel]] = {}
        for f in files:
            if f.sha256_hash: by_hash.setdefault(f.sha256_hash, []).append(f)
        exact = [{"sha256": h, "files": group, "wasted_bytes": sum(x.file_size for x in group[1:])}
                 for h, group in by_hash.items() if len(group) > 1]

        vectors = {f.file_id: self.index.vectorize(tokenize(self.get_text(f))) for f in files}
        near, similar_names = [], []
        for i, a in enumerate(files):
            for b in files[i + 1:]:
                if a.sha256_hash and a.sha256_hash == b.sha256_hash: continue  # Already listed as exact
                va, vb = vectors[a.file_id], vectors[b.file_id]
                if len(va) >= 5 and len(vb) >= 5:
                    sim = TFIDFIndex.cosine(va, vb)
                    if sim >= self.NEAR_DUP_THRESHOLD: near.append({"files": [a, b], "similarity": round(sim, 4)})
                name_sim = EditDistance.similarity(a.filename.rsplit(".", 1)[0].lower(), b.filename.rsplit(".", 1)[0].lower())
                if name_sim >= 0.8: similar_names.append({"files": [a, b], "similarity": round(name_sim, 4)})
        near.sort(key=lambda x: -x["similarity"])
        similar_names.sort(key=lambda x: -x["similarity"])
        return {"exact": exact, "near": near, "similar_names": similar_names,
                "wasted_bytes": sum(g["wasted_bytes"] for g in exact)}
