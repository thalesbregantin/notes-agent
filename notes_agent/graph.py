"""O pipeline como grafo em LangGraph: cada etapa é um nó, e o reparo é uma aresta condicional.

    guardrail -> generate -> verify -> (reparar?) -> repair -> verify -> fim

Faz o mesmo que `pipeline.make_note`, mas com o fluxo explícito e inspecionável. A gravação da nota
fica fora do grafo (em `service.create_note`): o grafo é puro e fácil de testar.
"""

from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from .fidelity import FidelityReport, check_note
from .guardrails import Match, quarantine
from .llm import LLM
from .pipeline import MAX_UNSUPPORTED, NoteResult, generate_note
from .schemas import Note


class State(TypedDict, total=False):
    text: str
    clean: str
    flagged: list[Match]
    note: Note
    report: FidelityReport
    repaired: bool


def build_graph(llm: LLM) -> Any:
    def guardrail(state: State) -> State:
        clean, flagged = quarantine(state["text"])
        return {"clean": clean, "flagged": flagged, "repaired": False}

    def generate(state: State) -> State:
        return {"note": generate_note(llm, state["clean"])}

    def verify(state: State) -> State:
        return {"report": check_note(state["note"], state["clean"])}

    def repair(state: State) -> State:
        bad = "; ".join(c.text for c in state["report"].unsupported)
        extra = f"\nRemova ou corrija estas afirmações sem apoio no texto: {bad}"
        return {"note": generate_note(llm, state["clean"], extra), "repaired": True}

    def needs_repair(state: State) -> Literal["repair", "done"]:
        too_many = state["report"].unsupported_ratio > MAX_UNSUPPORTED
        return "repair" if too_many and not state["repaired"] else "done"

    graph = StateGraph(State)
    graph.add_node("guardrail", guardrail)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)
    graph.add_node("repair", repair)
    graph.add_edge(START, "guardrail")
    graph.add_edge("guardrail", "generate")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges("verify", needs_repair, {"repair": "repair", "done": END})
    graph.add_edge("repair", "verify")
    return graph.compile()


def run_graph(text: str, llm: LLM) -> NoteResult:
    final = build_graph(llm).invoke({"text": text})
    return NoteResult(final["note"], final["report"], final["flagged"], final["repaired"])


def mermaid(llm: LLM) -> str:
    return str(build_graph(llm).get_graph().draw_mermaid())
