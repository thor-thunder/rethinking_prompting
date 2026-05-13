---
name: rethinking-prompting-with-atomic-agents
description: Build agentic prompting-strategy experiments in this repo using the atomic-agents framework. Use this skill whenever a task involves authoring a new prompting strategy (CoT, DiP, L2M, SBP, AnP, ToT, S-RF, MAD), wrapping the existing model/dataset pipeline behind a typed agent, or wiring an atomic-agents BaseAgent/BaseTool around the CoT + majority-voting workflow described in PROMPT.md.
---

# Rethinking Prompting × atomic-agents

This repository accompanies the ACL 2025 paper *"Rethinking the Role of Prompting Strategies in LLM Test-Time Scaling"*. The codebase already implements 8 prompting strategies, 6 datasets, and 6 LLM backends in plain Python (`main.py`, `model.py`, `dataset.py`, `prompts/`). This skill explains how to layer **atomic-agents** on top of that code so new experiments can be expressed as typed, composable agents instead of ad-hoc scripts.

Treat atomic-agents as **the** abstraction for any new agentic component added to this repo. Do **not** invent parallel agent/tool base classes.

## 1. Install (already done in this branch)

```bash
pip install atomic-agents
```

`atomic-agents==1.1.11` is pinned in `requirements.txt`. It pulls in `instructor`, `pydantic>=2`, `openai`, and `mcp` automatically.

## 2. Mental model

atomic-agents has four atoms. Learn these before writing code:

| Atom | File | Purpose |
| --- | --- | --- |
| `BaseIOSchema` | `atomic_agents.lib.base.base_io_schema` | Pydantic model for every agent/tool input & output. **Must** have a non-empty docstring — the class enforces it. |
| `SystemPromptGenerator` | `atomic_agents.lib.components.system_prompt_generator` | Composes a system prompt from `background`, `steps`, `output_instructions`, and optional `context_providers`. |
| `AgentMemory` | `atomic_agents.lib.components.agent_memory` | Stores chat history for multi-turn / iterative strategies (ToT, S-RF, MAD). |
| `BaseAgent` / `BaseAgentConfig` | `atomic_agents.agents.base_agent` | The runnable unit. Holds an `instructor`-wrapped client, model id, memory, prompt generator, and input/output schemas. Call `agent.run(input)` (sync) or `agent.run_async(input)` (streaming). |
| `BaseTool` | `atomic_agents.lib.base.base_tool` | Wrap a callable as `input_schema → run(params) → output_schema` so it can be exposed to an agent. |

The runtime contract is: **typed input → system prompt (built from generator + memory) → instructor-validated output**. Stick to this — do not hand-format prompt strings around it.

## 3. Repo-specific guidance

### 3.1 Prompting strategies are first-class

The paper's central empirical claim is that, under majority voting, simple **CoT** and **DiP** beat complex strategies as sampling scales. When you implement a new strategy as an atomic-agents agent:

- **Default to CoT + majority voting** (the template in `PROMPT.md`) unless the user explicitly asks for ToT / S-RF / MAD. Don't add multi-agent debate or tree branching to "improve" a task — the paper shows it usually hurts at scale.
- Sample N=16 with temperature ≈ 0.7, then majority-vote the `\boxed{...}` answers. Keep this loop outside the agent (in the caller), not inside the schema.
- Strategy names used elsewhere in the codebase: `DiP`, `CoT`, `L2M`, `SBP`, `AnP`, `ToT`, `S-RF`, `MAD`. Reuse those identifiers.

### 3.2 Map the existing pipeline onto atomic atoms

| Repo concept | atomic-agents equivalent |
| --- | --- |
| `prompts/*.py` strategy templates | `SystemPromptGenerator(background=..., steps=..., output_instructions=...)` |
| `model.py` LLM wrapper | the `instructor`-wrapped `client` passed into `BaseAgentConfig` |
| `dataset.py` row → question | a `BaseIOSchema` subclass (e.g. `QuestionInputSchema`) |
| `\boxed{answer}` extraction | a field on the output schema (e.g. `final_answer: str`) plus optional `reasoning: str` |
| Iterative strategies (ToT, S-RF, MAD) | multiple `BaseAgent`s composed in Python, sharing or branching `AgentMemory` |
| Majority voting in `eval_csv_*.py` | caller-side aggregation over N `agent.run(...)` calls |

### 3.3 Canonical agent skeleton for this repo

Use this shape for every new strategy. Adapt names, keep the structure:

```python
import instructor
from openai import OpenAI
from pydantic import Field
from atomic_agents.agents.base_agent import BaseAgent, BaseAgentConfig
from atomic_agents.lib.base.base_io_schema import BaseIOSchema
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator


class QuestionInputSchema(BaseIOSchema):
    """A single reasoning question to be answered with CoT + boxed final answer."""
    question: str = Field(..., description="The problem statement to solve.")
    exemplars: str | None = Field(default=None, description="Optional few-shot block (Q/A pairs) prepended to the prompt.")


class CoTAnswerSchema(BaseIOSchema):
    """Chain-of-thought reasoning followed by the final boxed answer."""
    key_principles: str = Field(..., description="One or two lines naming the concepts the question tests.")
    reasoning: str = Field(..., description="Step-by-step derivation.")
    final_answer: str = Field(..., description="The content that goes inside \\boxed{...} — number, expression, letter, or short string.")


def build_cot_agent(model: str = "gpt-4o-mini", api_key: str | None = None) -> BaseAgent:
    client = instructor.from_openai(OpenAI(api_key=api_key))
    prompt = SystemPromptGenerator(
        background=[
            "You answer reasoning questions using Chain-of-Thought.",
            "Your final answer always appears inside \\boxed{...}.",
        ],
        steps=[
            "Identify the key concepts the question tests.",
            "Solve the problem step by step.",
            "Double-check the result and emit the boxed answer.",
        ],
        output_instructions=[
            "Pick the \\boxed{...} format from the question type: number, expression, single capital letter, or shortest unambiguous string.",
        ],
    )
    return BaseAgent(BaseAgentConfig(
        client=client,
        model=model,
        system_prompt_generator=prompt,
        input_schema=QuestionInputSchema,
        output_schema=CoTAnswerSchema,
        model_api_parameters={"temperature": 0.7},
    ))
```

Majority voting stays in the caller:

```python
from collections import Counter

agent = build_cot_agent()
samples = [agent.run(QuestionInputSchema(question=q)).final_answer for _ in range(16)]
predicted = Counter(samples).most_common(1)[0][0]
```

### 3.4 When you need an iterative strategy

- **Self-Refine (S-RF):** two agents — `Drafter` and `Critic` — share an `AgentMemory`. Loop until the critic returns `done=True` on its output schema.
- **Multi-Agent Debate (MAD):** N independent agents (each its own `AgentMemory`), then a `Judge` agent whose input schema lists their answers.
- **Tree of Thoughts (ToT):** an `Expander` agent that returns `next_thoughts: list[str]` plus an `Evaluator` agent. Branch in Python — do **not** try to encode tree state in a single prompt.

For every iterative strategy, prefer many small agents with narrow schemas over one big agent doing everything. That is the whole point of "atomic" agents.

### 3.5 Tools (only when you actually need them)

If a strategy needs a calculator, code executor, or retrieval step, wrap it as a `BaseTool`:

```python
from atomic_agents.lib.base.base_tool import BaseTool, BaseToolConfig

class CalculatorInputSchema(BaseIOSchema):
    """A pure arithmetic expression to evaluate."""
    expression: str = Field(..., description="A safe Python arithmetic expression.")

class CalculatorOutputSchema(BaseIOSchema):
    """Result of evaluating the expression."""
    value: float = Field(..., description="Numeric result.")

class Calculator(BaseTool):
    input_schema = CalculatorInputSchema
    output_schema = CalculatorOutputSchema
    def run(self, params: CalculatorInputSchema) -> CalculatorOutputSchema:
        return CalculatorOutputSchema(value=float(eval(params.expression, {"__builtins__": {}})))
```

Don't add tools speculatively — the paper's headline finding is that complexity hurts. Add a tool only when the dataset requires it.

## 4. Working rules in this repo

These rules apply to any Claude session in this directory:

- **Editing files:** prefer `Edit` over `Write`. Never create new top-level Python modules when a small change to `main.py` / `model.py` / `dataset.py` suffices.
- **Don't reinvent prompts:** the canonical CoT scaffold lives in `PROMPT.md`. New agents should mirror its three-step structure (principles → reasoning → boxed answer) inside `SystemPromptGenerator`.
- **Schemas must have docstrings.** `BaseIOSchema.__pydantic_init_subclass__` raises `ValueError` otherwise.
- **Don't hard-code API keys.** Read `openai_api_key`, `openai_base_url`, `google_api_key`, `hf_token` from env or the existing config sites in `main.py` / `dataset.py`.
- **Determinism vs. scaling:** when reproducing paper numbers, sample with `temperature=0.7`, N=16, and majority-vote in the caller. When debugging a single trace, set `temperature=0` and N=1.
- **No emojis in code or commits.** Markdown badges in `readme.md` stay as-is.
- **Comments:** only for non-obvious *why*. The schema docstrings already explain *what*.
- **Tests / smoke checks:** if you change agent wiring, run a one-shot `agent.run(QuestionInputSchema(question="2+2=?"))` against a cheap model before declaring the change done.

## 5. Quick reference

```python
# Imports you almost always need
from atomic_agents.agents.base_agent import BaseAgent, BaseAgentConfig
from atomic_agents.lib.base.base_io_schema import BaseIOSchema
from atomic_agents.lib.base.base_tool import BaseTool, BaseToolConfig
from atomic_agents.lib.components.system_prompt_generator import (
    SystemPromptGenerator, SystemPromptContextProviderBase,
)
from atomic_agents.lib.components.agent_memory import AgentMemory
```

| Need | Call |
| --- | --- |
| Run one turn | `agent.run(input_schema_instance)` |
| Stream a turn | `async for partial in agent.run_async(input): ...` |
| Reset between questions | `agent.reset_memory()` |
| Inject dynamic context | `agent.register_context_provider("name", provider)` |
| Override response shape per-call | `agent.get_response(response_model=MyOtherSchema)` |

That is the full surface area you need for this repo. If a request can be expressed with the atoms above, do not introduce additional frameworks (LangChain, CrewAI, AutoGen, etc.).
