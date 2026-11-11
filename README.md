# notes-agent

Transforma texto e transcrições em notas do Obsidian, tratando como requisito de engenharia o que costuma falhar em agentes de resumo: o modelo errar o formato, inventar fatos e obedecer ordens escondidas no conteúdo.

```bash
uv sync --all-groups
uv run python -m notes_agent note examples/reuniao.txt --vault notas   # gera a nota (baseline offline)
uv run python -m notes_agent eval --failures                           # mede guardrail e fidelidade
uv run pytest                                                          # 25 testes, sem rede
```

## O que resolve

| Falha comum | O que o projeto faz |
| :--- | :--- |
| O modelo devolve JSON malformado e o programa quebra | **Saída estruturada:** o JSON é extraído, validado com Pydantic e, se falhar, o erro volta ao modelo numa nova tentativa (`structured.py`) |
| O resumo inclui números e fatos que não estavam no texto | **Checagem de fidelidade:** toda afirmação precisa ter apoio na origem (palavras de conteúdo e números). Se passar de 25% sem apoio, tenta um reparo e, se não resolver, marca `needs_review` |
| O texto transcrito manda no agente ("ignore as instruções...") | **Guardrail:** linhas suspeitas são removidas antes do modelo e registradas no frontmatter. O que sobra vai numa tag marcada como dado, com tags de fechamento forjadas removidas |
| Testar exige API key e dinheiro | LLM por interface: `FakeLLM` nos testes, `ExtractiveBaseline` offline, `OllamaLLM` e `AnthropicLLM` por HTTP |
| A nota sobrescreve outra ou escapa da pasta | Nome por data e slug, sem sobrescrever, sempre dentro do vault |

## Resultados medidos

`python -m notes_agent eval`. Os gabaritos estão em `evals/`: 61 linhas rotuladas para injection (24 ataques, 37 textos legítimos, entre eles casos difíceis de propósito) e 14 afirmações para fidelidade.

**Guardrail de injection.** Detectar injection é um problema de classe rara com custo assimétrico, como fraude. Por isso o relatório mostra a curva por limiar, não um número só:

| limiar | precisão | recall | F1 |
| ---: | ---: | ---: | ---: |
| 0.4 | 0.90 | 0.79 | 0.84 |
| **0.6 (padrão)** | 0.90 | 0.79 | 0.84 |
| 0.8 | 0.93 | 0.58 | 0.72 |
| 1.2 | 1.00 | 0.25 | 0.40 |

O padrão é 0,6 por uma decisão de custo: remover uma linha legítima da nota é barato e fica registrado; deixar passar uma injection custa caro. **Escolhi o limiar depois de ver a tabela**, então os números nesse ponto são otimistas.

Erros que o guardrail ainda comete:
- Perde paráfrases ("Quem estiver lendo isto como IA deve ignorar o resumo...") e ofuscação (`1gnore prev1ous instructions`).
- Sinaliza por engano texto que *fala sobre* injection e o legítimo "You are now ready to deploy".

**Fidelidade** (detectar afirmação sem apoio): precisão 1,00, recall 0,86 (6 de 7). Perde, por exemplo, afirmações inventadas que reaproveitam as palavras da origem.

## Limitações

- O guardrail é heurístico, com padrões em português e inglês. Não substitui um classificador treinado nem isolamento de privilégios: se o agente puder acionar ferramentas perigosas, a defesa real é limitar o que elas fazem.
- A fidelidade mede sobreposição lexical, não significado. Paráfrase forte pode parecer sem apoio, e uma frase com sentido trocado pode passar. O resultado serve para triagem e revisão humana.
- Os dois gabaritos são pequenos e foram escritos por mim.
- `OllamaLLM` e `AnthropicLLM` têm a requisição testada com HTTP simulado, mas ainda não foram validados contra um modelo real.
- O baseline extrativo não é IA: só reorganiza frases do texto. Serve de demo offline e de linha de base para comparar modelos.

## Roadmap

1. Transcrição local de áudio (faster-whisper) como entrada.
2. Grafo em LangGraph em volta do pipeline: roteamento por tipo de entrada, validação e gravação como nós explícitos.
3. Servidor MCP com `criar_nota` e `buscar_notas`.
4. Avaliação com modelo real (Ollama ou Claude) comparada ao baseline.

## Estrutura

```text
notes_agent/llm.py          # interface LLM, FakeLLM, baseline, Ollama, Anthropic
notes_agent/structured.py   # JSON validado com nova tentativa
notes_agent/guardrails.py   # detecção e quarentena de prompt injection
notes_agent/fidelity.py     # apoio de cada afirmação na origem
notes_agent/pipeline.py     # guardrail -> nota -> fidelidade -> reparo -> status
notes_agent/notes.py        # Markdown com frontmatter e gravação segura
notes_agent/evals.py        # métricas contra os gabaritos
evals/                      # injection.jsonl, fidelity.jsonl
tests/                      # 25 testes
```

## Licença

MIT.
