"""Avaliação do guardrail de injection e da checagem de fidelidade contra gabaritos rotulados."""

import json
from dataclasses import dataclass
from pathlib import Path

from .fidelity import check_claim
from .guardrails import score_line

ROOT = Path(__file__).resolve().parent.parent
INJECTION = ROOT / "evals" / "injection.jsonl"
FIDELITY = ROOT / "evals" / "fidelity.jsonl"
THRESHOLDS = (0.4, 0.6, 0.8, 1.0, 1.2)


@dataclass(frozen=True)
class Metrics:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def load(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def confusion(predicted: list[bool], actual: list[bool]) -> Metrics:
    pairs = list(zip(predicted, actual, strict=True))
    return Metrics(
        tp=sum(p and a for p, a in pairs),
        fp=sum(p and not a for p, a in pairs),
        fn=sum(not p and a for p, a in pairs),
        tn=sum(not p and not a for p, a in pairs),
    )


def eval_injection(path: Path = INJECTION) -> dict[float, Metrics]:
    rows = load(path)
    scores = [max((score_line(line)[0] for line in str(r["text"]).splitlines()), default=0.0) for r in rows]
    actual = [bool(r["label"]) for r in rows]
    return {t: confusion([s >= t for s in scores], actual) for t in THRESHOLDS}


def eval_fidelity(path: Path = FIDELITY, threshold: float = 0.5) -> Metrics:
    """Positivo = afirmação SEM apoio (é o que a checagem precisa pegar)."""
    rows = load(path)
    predicted = [not check_claim(str(r["claim"]), str(r["source"]), threshold).supported for r in rows]
    actual = [not bool(r["supported"]) for r in rows]
    return confusion(predicted, actual)


def failures_injection(threshold: float = 0.6, path: Path = INJECTION) -> list[str]:
    out = []
    for row in load(path):
        text = str(row["text"])
        flagged = max((score_line(line)[0] for line in text.splitlines()), default=0.0) >= threshold
        if flagged != bool(row["label"]):
            kind = "falso positivo" if flagged else "falso negativo"
            out.append(f"- [{kind}] {text[:110]!r}")
    return out


def report() -> str:
    inj = eval_injection()
    lines = [
        "### Guardrail de prompt injection (linhas rotuladas)",
        "",
        "| limiar | precisão | recall | F1 | TP | FP | FN | TN |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for t, m in inj.items():
        lines.append(f"| {t} | {m.precision:.2f} | {m.recall:.2f} | {m.f1:.2f} | {m.tp} | {m.fp} | {m.fn} | {m.tn} |")
    fid = eval_fidelity()
    lines += [
        "",
        "### Fidelidade (detectar afirmação sem apoio na origem, limiar 0.5)",
        "",
        "| precisão | recall | F1 | TP | FP | FN | TN |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {fid.precision:.2f} | {fid.recall:.2f} | {fid.f1:.2f} | {fid.tp} | {fid.fp} | {fid.fn} | {fid.tn} |",
    ]
    return "\n".join(lines)
