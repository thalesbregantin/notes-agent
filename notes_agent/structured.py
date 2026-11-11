"""Saída estruturada com validação e nova tentativa.

Pedir "responda só JSON" e chamar json.loads quebra quando o modelo erra o formato. Aqui o JSON é
extraído, validado contra um schema Pydantic e, se falhar, o erro volta ao modelo numa nova tentativa.
"""

import re

from pydantic import BaseModel

from .llm import LLM

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)


class StructuredOutputError(RuntimeError):
    pass


def extract_json(text: str) -> str:
    fenced = FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


def generate_structured[T: BaseModel](llm: LLM, model: type[T], system: str, prompt: str, max_retries: int = 2) -> T:
    attempt_prompt, last_error = prompt, ""
    for _ in range(max_retries + 1):
        raw = llm.complete(system, attempt_prompt)
        try:
            return model.model_validate_json(extract_json(raw))
        except ValueError as error:  # ValidationError herda de ValueError
            last_error = " ".join(str(error).split())[:300]
            attempt_prompt = (
                f"{prompt}\n\nSua resposta anterior era inválida ({last_error}). "
                "Responda apenas com o JSON no formato pedido."
            )
    raise StructuredOutputError(f"saída inválida após {max_retries + 1} tentativas: {last_error}")
