"""Uso:
python -m notes_agent eval [--failures]
python -m notes_agent note ARQUIVO [--vault PASTA] [--llm baseline|ollama|anthropic]
"""

import argparse
import sys
from pathlib import Path

from . import evals
from .llm import make_llm
from .notes import save_note
from .pipeline import make_note, meta_of


def cmd_eval(args: argparse.Namespace) -> None:
    print(evals.report())
    if args.failures:
        print("\nErros do guardrail no limiar padrão (0.6):")
        print("\n".join(evals.failures_injection()))


def cmd_note(args: argparse.Namespace) -> None:
    source = Path(args.file)
    result = make_note(source.read_text(encoding="utf-8"), make_llm(args.llm))
    path = save_note(Path(args.vault), result.note, meta_of(result, source.name))
    print(f"Nota salva em {path}")
    print(f"status: {result.status} | linhas de injection removidas: {len(result.flagged)}")
    for claim in result.report.unsupported:
        print(f"  sem apoio: {claim.text}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="notes_agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_eval = sub.add_parser("eval", help="mede guardrail e fidelidade")
    p_eval.add_argument("--failures", action="store_true")
    p_eval.set_defaults(fn=cmd_eval)
    p_note = sub.add_parser("note", help="gera uma nota a partir de um arquivo de texto")
    p_note.add_argument("file")
    p_note.add_argument("--vault", default="notas")
    p_note.add_argument("--llm", default="baseline", choices=["baseline", "ollama", "anthropic"])
    p_note.set_defaults(fn=cmd_note)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
