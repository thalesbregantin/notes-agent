"""Operações sobre o vault. É a camada que o servidor MCP, o grafo e a CLI compartilham."""

from collections import Counter
from pathlib import Path

from .llm import LLM
from .notes import parse_frontmatter, save_note
from .pipeline import make_note, meta_of
from .retrieval import BM25, CharTfidf, HybridRRF

MAX_TEXT_CHARS = 200_000
MAX_LIMIT = 20


def create_note(text: str, vault: Path, llm: LLM, source: str = "mcp") -> dict[str, object]:
    if not text.strip():
        raise ValueError("texto vazio")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"texto acima de {MAX_TEXT_CHARS} caracteres")
    result = make_note(text, llm)
    path = save_note(vault, result.note, meta_of(result, source))
    return {
        "file": path.name,
        "title": result.note.title,
        "status": result.status,
        "injection_lines_removed": len(result.flagged),
        "unsupported_claims": [c.text for c in result.report.unsupported],
    }


def _load(vault: Path) -> list[tuple[Path, dict[str, str], str]]:
    if not vault.is_dir():
        return []
    notes = []
    for path in sorted(vault.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        notes.append((path, meta, body))
    return notes


def search_notes(query: str, vault: Path, limit: int = 5) -> list[dict[str, object]]:
    limit = max(1, min(limit, MAX_LIMIT))
    notes = _load(vault)
    if not notes or not query.strip():
        return []
    texts = [f"{meta.get('title', path.stem)}\n{body}" for path, meta, body in notes]
    index = HybridRRF(BM25(texts), CharTfidf(texts))
    hits: list[dict[str, object]] = []
    for i in index.search(query, limit):
        path, meta, body = notes[i]
        hits.append(
            {
                "file": path.name,
                "title": meta.get("title", path.stem),
                "status": meta.get("status", ""),
                "snippet": " ".join(body.split())[:200],
            }
        )
    return hits


def vault_stats(vault: Path) -> dict[str, object]:
    notes = _load(vault)
    tags: Counter[str] = Counter()
    for _, meta, _ in notes:
        raw = meta.get("tags", "").strip("[]")
        tags.update(t.strip() for t in raw.split(",") if t.strip())
    return {
        "notes": len(notes),
        "by_status": dict(Counter(meta.get("status", "?") for _, meta, _ in notes)),
        "injection_lines_removed": sum(int(meta.get("injection_lines_removed", "0") or 0) for _, meta, _ in notes),
        "top_tags": dict(tags.most_common(10)),
    }
