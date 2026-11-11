"""Checagem de fidelidade: cada afirmação da nota precisa ter apoio no texto de origem.

Regras determinísticas, sem chamar modelo:
1. Todo número citado na afirmação precisa aparecer na origem.
2. A fração das palavras de conteúdo da afirmação que aparece em uma janela de até 3 frases
   consecutivas da origem precisa chegar ao limiar.

Limitação: mede sobreposição lexical. Paráfrase forte pode parecer sem apoio, e uma frase que
reaproveita as palavras da origem com sentido trocado pode passar. Por isso o resultado vira
"needs_review" para revisão humana, e não uma sentença.
"""

from dataclasses import dataclass

from .schemas import Note
from .textutil import content_tokens, numbers, split_sentences

WINDOW = 3


@dataclass(frozen=True)
class ClaimResult:
    text: str
    score: float
    supported: bool
    missing_numbers: tuple[str, ...]


@dataclass(frozen=True)
class FidelityReport:
    claims: list[ClaimResult]

    @property
    def unsupported(self) -> list[ClaimResult]:
        return [c for c in self.claims if not c.supported]

    @property
    def unsupported_ratio(self) -> float:
        return len(self.unsupported) / len(self.claims) if self.claims else 0.0


def _windows(source: str) -> list[set[str]]:
    sentences = split_sentences(source) or [source]
    tokens = [content_tokens(s) for s in sentences]
    out = []
    for i in range(len(tokens)):
        merged: set[str] = set()
        for j in range(i, min(i + WINDOW, len(tokens))):
            merged |= tokens[j]
        out.append(merged)
    return out


def check_claim(claim: str, source: str, threshold: float = 0.5) -> ClaimResult:
    claim_tokens = content_tokens(claim)
    missing = tuple(sorted(numbers(claim) - numbers(source)))
    if not claim_tokens:
        return ClaimResult(claim, 1.0, not missing, missing)
    score = max((len(claim_tokens & w) / len(claim_tokens) for w in _windows(source)), default=0.0)
    return ClaimResult(claim, round(score, 3), score >= threshold and not missing, missing)


def claims_of(note: Note) -> list[str]:
    return [*split_sentences(note.summary), *note.key_points]


def check_note(note: Note, source: str, threshold: float = 0.5) -> FidelityReport:
    return FidelityReport([check_claim(c, source, threshold) for c in claims_of(note)])
