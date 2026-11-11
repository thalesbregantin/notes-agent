"""Busca nas notas: BM25 + TF-IDF de n-gramas de caracteres, combinados por RRF.

Adaptado do projeto rag-evals (mesmo autor), onde essas estratégias foram comparadas num gabarito.
"""

import math
import re
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"[a-zà-ÿ0-9_]+", re.I)
STOP = frozenset(
    (
        "a o as os um uma de do da dos das em no na nos nas por para com sem que se e ou the an and of to in on is are"
    ).split()
)


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s", "ção", "mente"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in (w.lower() for w in TOKEN_RE.findall(text)) if t not in STOP]


def _top(scores: dict[int, float], k: int) -> list[int]:
    return [i for i, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) or 1.0
        self.postings: dict[str, list[int]] = defaultdict(list)
        for i, tf in enumerate(self.tfs):
            for term in tf:
                self.postings[term].append(i)
        n = len(texts)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def search(self, query: str, k: int) -> list[int]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(tokenize(query)):
            for i in self.postings.get(term, ()):
                tf = self.tfs[i][term]
                norm = 1 - self.b + self.b * self.lengths[i] / self.avg_len
                scores[i] += self.idf[term] * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        return _top(scores, k)


class CharTfidf:
    def __init__(self, texts: list[str], ngram: tuple[int, int] = (3, 5)) -> None:
        self.ngram = ngram
        grams = [Counter(self._grams(t)) for t in texts]
        df = Counter(g for c in grams for g in c)
        n = len(texts)
        self.idf = {g: math.log((1 + n) / (1 + d)) + 1 for g, d in df.items()}
        self.vecs = [self._weigh(c) for c in grams]

    def _grams(self, text: str) -> list[str]:
        lo, hi = self.ngram
        out = []
        for word in TOKEN_RE.findall(text.lower()):
            if word in STOP:
                continue
            padded = f" {word} "
            for n in range(lo, hi + 1):
                out += [padded[i : i + n] for i in range(len(padded) - n + 1)]
        return out

    def _weigh(self, counts: Counter[str]) -> dict[str, float]:
        vec = {g: (1 + math.log(c)) * self.idf.get(g, 0.0) for g, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {g: v / norm for g, v in vec.items()}

    def search(self, query: str, k: int) -> list[int]:
        q = self._weigh(Counter(self._grams(query)))
        scores = {}
        for i, vec in enumerate(self.vecs):
            s = sum(w * vec.get(g, 0.0) for g, w in q.items())
            if s > 0:
                scores[i] = s
        return _top(scores, k)


class HybridRRF:
    def __init__(self, bm25: BM25, char: CharTfidf, k_rrf: int = 60, depth: int = 50) -> None:
        self.parts: list[BM25 | CharTfidf] = [bm25, char]
        self.k_rrf, self.depth = k_rrf, depth

    def search(self, query: str, k: int) -> list[int]:
        fused: dict[int, float] = defaultdict(float)
        for part in self.parts:
            for rank, idx in enumerate(part.search(query, self.depth), start=1):
                fused[idx] += 1 / (self.k_rrf + rank)
        return _top(fused, k)
