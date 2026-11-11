"""Interface mínima de LLM e as implementações usadas no projeto.

- FakeLLM: respostas roteirizadas, para testes determinísticos.
- ExtractiveBaseline: monta a nota só com frases do texto (sem IA). Serve de demo offline e de linha de base.
- OllamaLLM e AnthropicLLM: modelos reais por HTTP, sem SDK. Recebem `post` por injeção para serem testáveis.
"""

import json
import os
import re
import urllib.request
from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any, Protocol
from urllib.parse import urlparse

from .textutil import content_tokens, split_sentences

Post = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


def post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: float) -> dict[str, Any]:
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"esquema de URL não permitido: {url}")
    request = urllib.request.Request(  # noqa: S310 (esquema validado acima)
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    return data


class LLM(Protocol):
    def complete(self, system: str, prompt: str) -> str: ...


class FakeLLM:
    """Devolve respostas roteirizadas em ordem (a última se repete) ou usa uma função."""

    def __init__(self, responses: Sequence[str] | Callable[[str, str], str]) -> None:
        self._responses = responses
        self._index = 0
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if callable(self._responses):
            return self._responses(system, prompt)
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return response


class ExtractiveBaseline:
    """Nota extrativa: título, resumo e pontos vêm de frases do próprio texto. Não é IA."""

    TAG_RE = re.compile(r"<conteudo_nao_confiavel>(.*?)</conteudo_nao_confiavel>", re.S)

    def complete(self, system: str, prompt: str) -> str:
        match = self.TAG_RE.search(prompt)
        text = match.group(1) if match else prompt
        sentences = split_sentences(text) or [text.strip() or "Sem conteúdo"]
        summary = " ".join(sentences[:2])
        if len(summary) < 20:
            summary = (summary + " (conteúdo curto)").ljust(20, ".")
        counts = Counter(t for s in sentences for t in content_tokens(s))
        tags = [t for t, _ in counts.most_common(3)]
        title = sentences[0][:60].strip(" .") or "Nota"
        return json.dumps(
            {"title": title.ljust(3, "."), "summary": summary, "key_points": sentences[:5], "tags": tags},
            ensure_ascii=False,
        )


class OllamaLLM:
    def __init__(
        self, model: str = "llama3.1", host: str | None = None, post: Post = post_json, timeout: float = 120
    ) -> None:
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self._post, self._timeout = post, timeout

    def complete(self, system: str, prompt: str) -> str:
        body = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        return str(self._post(f"{self.host}/api/generate", {}, body, self._timeout)["response"])


class AnthropicLLM:
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self, model: str | None = None, api_key: str | None = None, post: Post = post_json, timeout: float = 60
    ) -> None:
        self.model = model or os.environ.get("NOTES_AGENT_MODEL", "claude-haiku-5-5")
        self._key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self._key:
            raise ValueError("ANTHROPIC_API_KEY não definida")
        self._post, self._timeout = post, timeout

    def complete(self, system: str, prompt: str) -> str:
        body = {
            "model": self.model,
            "max_tokens": 2048,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"x-api-key": self._key, "anthropic-version": "2023-06-01"}
        response = self._post(self.URL, headers, body, self._timeout)
        return "".join(block.get("text", "") for block in response["content"])


def make_llm(name: str) -> LLM:
    if name == "baseline":
        return ExtractiveBaseline()
    if name == "ollama":
        return OllamaLLM()
    if name == "anthropic":
        return AnthropicLLM()
    raise ValueError(f"LLM desconhecido: {name}")
