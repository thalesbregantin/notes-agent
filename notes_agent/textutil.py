"""Utilidades de texto compartilhadas: sentenças, tokens de conteúdo e números."""

import re

STOP = frozenset(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sobre entre e ou que se "
    "foi ser são era está estão vai vão ao aos à the an and or of to in on at by for with from is are was "
    "were be been it its this that these those as than then there their they them he she we you i".split()
)
TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]+(?:[.,][0-9]+)?", re.I)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s", "ção", "mente"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            return word[: -len(suffix)]
    return word


def content_tokens(text: str) -> set[str]:
    """Palavras de conteúdo (sem stopwords, com stemming leve). Números ficam de fora."""
    words = (w.lower() for w in TOKEN_RE.findall(text))
    return {_stem(w) for w in words if w not in STOP and len(w) >= 3 and not w[0].isdigit()}


def numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in NUMBER_RE.findall(text)}
