# Rethinking Prompting

Quick start for Claude Code sessions.

## ⚡ Quick Start

```bash
./init                # Setup project (uv, dependencies)
./init --all          # Also setup atomic-agents
```

See [readme.md](readme.md) for the research paper and full documentation.

## 📚 Key Files

| File | Purpose |
|------|---------|
| **model.py** | LLM interfaces (vLLM, OpenAI, Gemini) |
| **dataset.py** | Dataset loading, parsing, evaluation |
| **main.py** | Orchestration & prompting strategies |
| **prompts/** | Strategy templates (DiP, CoT, ToT, etc.) |

## 🔧 Common Commands

```bash
# Run with uv
uv run python main.py --help

# List available models
uv run python main.py --list-models

# Run a strategy
uv run python main.py --model gpt-4o-mini --strategy cot --dataset gsm8k
```

## 🤖 Atomic Agents

To use with atomic-agents framework:
```bash
./init --all
cd ../atomic-agents
```

See atomic-agents [README](../atomic-agents/README.md) for integration details.

## 📝 Notes

- All dependencies managed by `uv`
- Python 3.11+ required
- Set API keys via environment variables
- See `main.py` for configuration options
