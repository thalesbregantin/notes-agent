"""Guardrail determinístico contra prompt injection em conteúdo transcrito.

O texto que entra no agente (áudio, página, PDF) não é confiável: pode conter ordens dirigidas ao modelo.
A defesa tem duas camadas: (1) linhas suspeitas são removidas antes do LLM e registradas na nota;
(2) o que sobra vai dentro de uma tag marcada como DADO, nunca como instrução.

É uma heurística por padrões, então tem falsos negativos (paráfrases) e falsos positivos (texto que
fala sobre injection). `python -m notes_agent eval` mede os dois.
"""

import re
from dataclasses import dataclass

UNTRUSTED_TAG = "conteudo_nao_confiavel"

# (padrão, peso, rótulo). Linha com soma de pesos >= THRESHOLD é sinalizada.
PATTERNS: list[tuple[re.Pattern[str], float, str]] = [
    (
        re.compile(
            r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,30}"
            r"\b(instructions?|prompts?|rules?|guidelines?|told)\b",
            re.I,
        ),
        1.0,
        "ignorar-instrucoes-en",
    ),
    (
        re.compile(
            r"\b(ignore|desconsidere|esque[çc]a|descarte)\b.{0,40}\b(anteriores?|acima|tudo|todas?)\b.{0,30}"
            r"\b(instru[çc][õo]es|regras|orienta[çc][õo]es|acima|ordens)?",
            re.I,
        ),
        1.0,
        "ignorar-instrucoes-pt",
    ),
    (re.compile(r"\bforget everything\b", re.I), 1.0, "esquecer-tudo"),
    (
        re.compile(
            r"\b(reveal|repeat|print|show|display|mostre|revele|repita)\b.{0,40}"
            r"\b(system prompt|hidden instructions|prompt de sistema|prompt do sistema|instru[çc][õo]es ocultas)\b",
            re.I,
        ),
        1.0,
        "vazar-prompt",
    ),
    (re.compile(r"\b(you are now|from now on you|a partir de agora voc[êe])\b", re.I), 0.6, "troca-de-papel"),
    (re.compile(r"\b(developer mode|modo desenvolvedor|sem restri[çc][õo]es|\bDAN\b)", re.I), 0.6, "jailbreak"),
    (re.compile(r"^\s*(system|assistant|sistema)\s*:", re.I), 0.6, "marcador-de-papel"),
    (re.compile(r"<\|im_(start|end)\|>|\[/?INST\]|###\s*instruction", re.I), 1.0, "token-de-chat"),
    (re.compile(r"\b(new instructions?|novas? instru[çc][õo]es)\s*:", re.I), 0.6, "novas-instrucoes"),
    (re.compile(r"\b(do not|don't|n[ãa]o)\s+(summari[sz]e|resuma|follow|siga|obey)\b", re.I), 0.6, "nao-resumir"),
    (
        re.compile(
            r"\b(call|use|invoke|chame|use a ferramenta|execute o comando)\b.{0,30}"
            r"\b(delete|tool|rm -rf|ferramenta)\b",
            re.I,
        ),
        0.6,
        "acionar-ferramenta",
    ),
    (re.compile(r"\b(send|envie|enviar|post|upload)\b.{0,60}https?://", re.I), 0.6, "exfiltrar-para-url"),
    (re.compile(r"\b(stop summari[sz]ing|pare de resumir)\b", re.I), 0.6, "parar-de-resumir"),
]
THRESHOLD = 0.6


@dataclass(frozen=True)
class Match:
    line_no: int
    line: str
    score: float
    labels: tuple[str, ...]


def score_line(line: str) -> tuple[float, tuple[str, ...]]:
    hits = [(weight, label) for pattern, weight, label in PATTERNS if pattern.search(line)]
    return sum(w for w, _ in hits), tuple(label for _, label in hits)


def scan(text: str, threshold: float = THRESHOLD) -> list[Match]:
    matches = []
    for number, line in enumerate(text.splitlines(), start=1):
        score, labels = score_line(line)
        if score >= threshold:
            matches.append(Match(number, line.strip(), score, labels))
    return matches


def is_injection(text: str, threshold: float = THRESHOLD) -> bool:
    return bool(scan(text, threshold))


def quarantine(text: str, threshold: float = THRESHOLD) -> tuple[str, list[Match]]:
    """Remove as linhas sinalizadas. Devolve o texto limpo e o que foi removido."""
    flagged = scan(text, threshold)
    drop = {m.line_no for m in flagged}
    kept = [line for number, line in enumerate(text.splitlines(), start=1) if number not in drop]
    return "\n".join(kept), flagged


def wrap_untrusted(text: str) -> str:
    """Isola o conteúdo numa tag. Remove tags de fechamento forjadas que tentariam escapar do bloco."""
    safe = re.sub(rf"</?\s*{UNTRUSTED_TAG}\s*>", "", text, flags=re.I)
    return f"<{UNTRUSTED_TAG}>\n{safe}\n</{UNTRUSTED_TAG}>"
