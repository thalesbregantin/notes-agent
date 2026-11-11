"""Renderiza a nota em Markdown com frontmatter do Obsidian e grava sem sobrescrever."""

import re
import unicodedata
from datetime import date
from pathlib import Path

from .schemas import Note


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:60] or "nota"


def render_markdown(note: Note, meta: dict[str, str | int | float]) -> str:
    front = {"title": note.title, **meta, "tags": note.tags}
    lines = ["---"]
    for key, value in front.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(value)}]")
        else:
            lines.append(f"{key}: {str(value).replace(chr(10), ' ')}")
    lines += ["---", "", f"# {note.title}", "", note.summary, "", "## Pontos-chave", ""]
    lines += [f"- {p}" for p in note.key_points]
    return "\n".join(lines) + "\n"


def save_note(vault: Path, note: Note, meta: dict[str, str | int | float]) -> Path:
    """Grava `<data>-<slug>.md` dentro de `vault`. Nunca sobrescreve: acrescenta -2, -3..."""
    vault.mkdir(parents=True, exist_ok=True)
    base = f"{date.today().isoformat()}-{slugify(note.title)}"
    path, counter = vault / f"{base}.md", 2
    while path.exists():
        path = vault / f"{base}-{counter}.md"
        counter += 1
    path.write_text(render_markdown(note, meta), encoding="utf-8")
    return path


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Separa o frontmatter simples (`chave: valor`) do corpo da nota."""
    if not text.startswith("---\n"):
        return {}, text
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        return {}, text
    meta = {}
    for line in head.splitlines():
        key, colon, value = line.partition(":")
        if colon:
            meta[key.strip()] = value.strip()
    return meta, body.strip()
