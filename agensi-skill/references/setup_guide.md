# 🚀 Setup Guide: Connecting notes-agent to your AI Agent

This guide is for **you, the human**, to run once in your own terminal, outside of any AI agent session. The skill itself never clones, installs, or executes anything — it only assumes the `notes-agent` MCP server is already running when the agent calls its tools.

---

## 1. Prerequisites

- Python 3.10+ installed
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or `pip`
- An existing Obsidian vault folder on your machine

Install the engine yourself, in your own shell (do not ask an AI agent to run this for you):
```bash
git clone https://github.com/thalesbregantin/notes-agent.git
cd notes-agent
uv sync --extra mcp
```

Review the source before running it, same as you would for any third-party tool.

---

## 2. Configuration by Agent

The commands below also go in your own terminal, not in an agent chat.

### A. Claude Code (CLI)
Run a single command in your terminal:
```bash
claude mcp add notes-agent \
  --env NOTES_AGENT_VAULT=/absolute/path/to/your/obsidian/vault \
  -- uv run --extra mcp --directory /path/to/notes-agent python -m notes_agent.mcp_server
```

---

### B. Cursor IDE
Open `~/.cursor/mcp.json` (or add via Cursor Settings > Features > MCP) and paste:

```json
{
  "mcpServers": {
    "notes-agent": {
      "command": "uv",
      "args": [
        "run",
        "--extra",
        "mcp",
        "--directory",
        "/path/to/notes-agent",
        "python",
        "-m",
        "notes_agent.mcp_server"
      ],
      "env": {
        "NOTES_AGENT_VAULT": "/absolute/path/to/your/obsidian/vault",
        "NOTES_AGENT_LLM": "baseline"
      }
    }
  }
}
```

---

### C. Claude Desktop
Open your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add `notes-agent` under `"mcpServers"` with the same JSON block shown for Cursor above.

---

## 3. Selecting the LLM Mode (`NOTES_AGENT_LLM`)

The MCP server supports three engine modes:
- `baseline` *(Default)*: Deterministic, 100% offline, zero-token cost. Fast and private.
- `ollama`: Uses a local model running on your computer via Ollama (e.g., `llama3.2` or `mistral`).
- `anthropic`: Uses Claude directly. This mode is optional and off by default — only enable it by setting your own `ANTHROPIC_API_KEY` in your local MCP config if you want it; the skill never requests, stores, or transmits this key itself.

---

## 4. Testing the Connection

Once added, open your agent and say:
> *"Crie uma nota rápida no meu Obsidian sobre a arquitetura de RAG híbrido que discutimos hoje."*

The agent will execute `criar_nota` and confirm that your note has been saved with full frontmatter!

