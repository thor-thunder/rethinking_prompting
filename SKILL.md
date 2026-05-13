---
name: atomic-agents
description: Build LLM apps with the atomic-agents Python framework (BrainBlend-AI) — single-responsibility AtomicAgents with Pydantic input/output schemas, explicit orchestration in plain Python, and tools that never auto-invoke. Use this skill whenever the user wants to build a chatbot, multi-agent pipeline, RAG bot, MCP client, or any agentic LLM workflow with atomic-agents, or asks you to wrap an existing prompt/strategy (e.g. CoT, ToT, Self-Refine, Multi-Agent Debate) as a typed agent.
---

# atomic-agents

## What this is

[atomic-agents](https://github.com/BrainBlend-AI/atomic-agents) is a small, opinionated framework for building agentic LLM applications by **composing single-purpose pieces** — agents, tools, and context providers — each with explicit Pydantic input/output schemas. It is built on top of [Instructor](https://github.com/instructor-ai/instructor) and Pydantic.

The maintainers position it against LangChain / CrewAI / AutoGen:

> While existing frameworks for agentic AI focus on building autonomous multi-agent systems, they often lack the control and predictability required for real-world applications.

Four values drive every design choice: **modularity, predictability, extensibility, control**. The LEGO-block metaphor is theirs — and worth taking literally when writing code.

Docs root: <https://brainblend-ai.github.io/atomic-agents/>

## Version reality (read this first)

| Track | API names | Python | Installable here? |
| --- | --- | --- | --- |
| **v2.x (current docs)** | `AtomicAgent`, `AgentConfig`, `ChatHistory`, `fetch_mcp_tools_async` | **3.12+** | Only on Python 3.12+ |
| **v1.1.x (legacy, pinned in `requirements.txt` of this repo)** | `BaseAgent`, `BaseAgentConfig`, `AgentMemory`, `MCPToolFactory` | 3.11 OK | Yes (this env is 3.11) |

The whole skill below is written against **v2** because that is what the docs teach and what `pip install atomic-agents` returns on Python 3.12+. If you are stuck on Python 3.11 (as this repo's `conda` env is), apply the v1 translation table at the bottom of the file before running any snippet.

```bash
pip install atomic-agents          # v2.x on Py 3.12+, v1.1.11 on Py 3.11
```

## The five atoms

| Atom | Import | Job |
| --- | --- | --- |
| **Schema** | `from atomic_agents import BaseIOSchema` | A Pydantic model with a **required non-empty docstring**. Used for every agent/tool input and output. |
| **SystemPromptGenerator** | `from atomic_agents.context import SystemPromptGenerator` | Composes the system prompt from three lists — `background`, `steps`, `output_instructions` — plus optional context providers. Don't hardcode prompt strings. |
| **ChatHistory** | `from atomic_agents.context import ChatHistory` | Multi-turn memory. One per agent, or share across agents to fan-in conversation state. |
| **AtomicAgent** | `from atomic_agents import AtomicAgent, AgentConfig` | The runnable. Generic-typed on its input and output schemas: `AtomicAgent[InputSchema, OutputSchema]`. |
| **BaseTool** | `from atomic_agents import BaseTool, BaseToolConfig` | `input_schema → run(params) → output_schema`. **Never auto-invoked by an agent** — see the Tools section. |

If a request can be expressed with these five, do not pull in LangChain / CrewAI / LangGraph alongside. The whole point is the small surface area.

## Hello world (canonical, from the v2 quickstart)

```python
import os, instructor, openai
from atomic_agents import AtomicAgent, AgentConfig, BasicChatInputSchema, BasicChatOutputSchema
from atomic_agents.context import ChatHistory

history = ChatHistory()
client = instructor.from_openai(openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")))

agent = AtomicAgent[BasicChatInputSchema, BasicChatOutputSchema](
    config=AgentConfig(client=client, model="gpt-5-mini", history=history)
)

reply = agent.run(BasicChatInputSchema(chat_message="hi"))
print(reply.chat_message)
```

Two idioms to internalize from this snippet:

1. **Generic-type the agent class** — `AtomicAgent[InputSchema, OutputSchema](...)`. Do not pass schemas via `AgentConfig(input_schema=..., output_schema=...)`; that was the v1 idiom and is now discouraged.
2. **Always pass a schema instance to `.run()`** — never a raw string.

Quickstart files to read in order: `atomic-examples/quickstart/1_0_basic_chatbot.py` → `4_basic_chatbot_different_providers.py`.

## Custom schemas + SystemPromptGenerator

This is the shape you reach for once you outgrow the basic chat schemas:

```python
from pydantic import Field
from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator, ChatHistory

class QuestionInput(BaseIOSchema):
    """A single reasoning question to be answered with CoT."""
    question: str = Field(..., description="The problem statement.")

class CoTOutput(BaseIOSchema):
    """Chain-of-thought reasoning followed by the final boxed answer."""
    key_principles: str = Field(..., description="One or two lines naming the concepts the question tests.")
    reasoning: str = Field(..., description="Step-by-step derivation.")
    final_answer: str = Field(..., description="The content that goes inside \\boxed{...}.")

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
        "Pick the box format from the question type: number, expression, single capital letter, or shortest unambiguous string.",
    ],
)

agent = AtomicAgent[QuestionInput, CoTOutput](
    config=AgentConfig(client=client, model="gpt-5-mini",
                       history=ChatHistory(), system_prompt_generator=prompt)
)
```

`BaseIOSchema._validate_description` will raise `ValueError` at class-definition time if you forget the docstring. That's a feature — every schema doubles as LLM-visible documentation.

## Orchestration: five named patterns, all plain Python

Source: <https://brainblend-ai.github.io/atomic-agents/guides/orchestration.html>. There is **no `Orchestrator` class** — the framework deliberately leaves control flow to you. Pick a pattern and write the loop in `main.py`.

### 1. Sequential pipeline (schema chaining)
Agent A's output schema **is** agent B's input schema. That's the whole mechanism.

```python
classify_agent = AtomicAgent[Question, Classification](...)
solve_agent    = AtomicAgent[Classification, Solution](...)

classification = classify_agent.run(Question(text=q))
solution       = solve_agent.run(classification)
```

Canonical example: `atomic-examples/deep-research/` — a `ResearchState` object is threaded through several single-responsibility agents in a plain Python loop.

### 2. Tool orchestration / choice agent (`Union` output)
Let the agent pick which downstream tool to call by emitting a discriminated-union output:

```python
class AgentChoice(BaseIOSchema):
    """Decision about which tool to invoke."""
    tool_parameters: SearchTool.input_schema | CalculatorTool.input_schema

choice = router.run(user_query)
if isinstance(choice.tool_parameters, SearchTool.input_schema):
    result = search_tool.run(choice.tool_parameters)
else:
    result = calculator_tool.run(choice.tool_parameters)
```

Canonical example: `atomic-examples/orchestration-agent/`.

### 3. Router (classifier + dispatch table)
Classifier agent outputs `category: Literal["math", "code", "trivia"]`; the dispatcher picks the worker agent.

### 4. Parallel execution
Plain `asyncio.gather` over `run_async`:

```python
a, b = await asyncio.gather(agent_a.run_async(x), agent_b.run_async(y))
```

### 5. Supervisor / critic loop
A validator agent loops on the worker's output until it emits `approved=True`. This is the atomic-agents idiom for Self-Refine.

> Every agent has a single responsibility and reads/contributes to a shared state object. The loop itself lives in `main.py` as plain Python — no megagent, no hidden control flow.
> — *deep-research example README*

## Tools — they never auto-invoke

From the Tools guide, verbatim:

> There is no `tools=[...]` argument anywhere in the framework, and that is intentional. You decide when to call it.

Two recommended patterns:

**A. Direct call** — agent's output schema *is* the tool's input schema:
```python
tool_input = agent.run(user_query)        # output schema matches tool input
tool_result = tool.run(tool_input)
```

**B. Choice agent** — as shown in pattern 2 above.

The pre-built tool registry is **Atomic Forge**: tools are downloaded into your repo via the CLI rather than imported from a black-box package — same philosophy of control.

Implement a custom tool exactly like an agent's I/O contract:

```python
from atomic_agents import BaseTool, BaseToolConfig, BaseIOSchema

class CalcIn(BaseIOSchema):
    """A pure arithmetic expression to evaluate."""
    expression: str = Field(..., description="A safe Python arithmetic expression.")

class CalcOut(BaseIOSchema):
    """Result of evaluating the expression."""
    value: float = Field(..., description="Numeric result.")

class Calculator(BaseTool):
    input_schema = CalcIn
    output_schema = CalcOut
    def run(self, params: CalcIn) -> CalcOut:
        return CalcOut(value=float(eval(params.expression, {"__builtins__": {}})))
```

## Context providers (dynamic system-prompt injection)

For data that varies per turn — current date, retrieved RAG chunks, user profile — subclass `BaseDynamicContextProvider` and register it with the agent:

```python
from atomic_agents.context import BaseDynamicContextProvider
from datetime import date

class CurrentDateProvider(BaseDynamicContextProvider):
    def get_info(self) -> str:
        return f"Today is {date.today().isoformat()}."

agent.register_context_provider("date", CurrentDateProvider(title="Current Date"))
```

The `SystemPromptGenerator` automatically appends a `# EXTRA INFORMATION AND CONTEXT` section with each registered provider's output. Canonical example: `atomic-examples/rag-chatbot/` — the retrieved chunks are surfaced via a context provider rather than crammed into the user message.

## MCP integration

```python
from atomic_agents.connectors.mcp import fetch_mcp_tools_async, MCPTransportType

tools = await fetch_mcp_tools_async(
    server_url="http://localhost:8000",
    transport_type=MCPTransportType.HTTP_STREAM,   # or STDIO, SSE
)
```

Tools discovered over MCP plug into the same **choice-agent** pattern as local tools — they aren't autonomously invoked. Canonical example: `atomic-examples/mcp-agent/`.

## Streaming

| Method | Returns | Use when |
| --- | --- | --- |
| `agent.run(x)` | full output | default |
| `agent.run_async(x)` | full output (awaitable) | parallel orchestration with `asyncio.gather` |
| `agent.run_stream(x)` | sync generator of partials | CLI, progressive UI |
| `agent.run_async_stream(x)` | async generator of partials | async server endpoints |

Stream loop:
```python
async for partial in agent.run_async_stream(user_input):
    render(partial)        # partial is your output schema with fields filling in
```

## Idioms — do / don't

**Do**
- One responsibility per agent. If you find yourself adding a third unrelated field to an output schema, split the agent.
- Align schemas across handoffs. Output of A *is* input of B — refactor schemas to make this literally true, don't bridge with adapter code.
- Keep orchestration in plain Python where you can read it, log it, and breakpoint it.
- Use `SystemPromptGenerator(background=..., steps=..., output_instructions=...)`; treat hardcoded multi-line prompt strings as a smell.
- Give every `BaseIOSchema` a real docstring — it becomes the LLM-visible description.

**Don't**
- Don't expect autonomous tool-calling — there is no `tools=[]` arg.
- Don't pass raw strings to `.run()` — always a schema instance.
- Don't build an "Orchestrator" class. The plain-Python loop *is* the orchestration.
- Don't reach for v1 names (`BaseAgent`, `BaseAgentConfig`, `AgentMemory`, `MCPToolFactory`) when working against current docs — see translation table.

## Examples worth opening (`atomic-examples/`)

| Example | What it teaches |
| --- | --- |
| `quickstart/` | Graded intro, 4 files |
| `orchestration-agent/` | Tool-orchestration / choice-agent pattern |
| `deep-research/` | Sequential pipeline + shared state |
| `rag-chatbot/` | Context provider for retrieved chunks |
| `mcp-agent/` | STDIO / SSE / HTTP_STREAM transports |
| `web-search-agent/` | External tool integration |
| `fastapi-memory/` | Serving an agent + persisting history |
| `hooks-example/` | Observability and error handling |
| `basic-multimodal/`, `nested-multimodal/` | Image inputs |
| `youtube-summarizer/`, `youtube-to-recipe/` | End-to-end pipelines |

Browse: <https://github.com/BrainBlend-AI/atomic-agents/tree/main/atomic-examples>

## v1 → v2 translation table

When working in this repo (Python 3.11, pinned `atomic-agents==1.1.11`), rename as you go:

| v2 (docs)                          | v1.1.x (installed here)                 |
| ---------------------------------- | --------------------------------------- |
| `AtomicAgent[In, Out](config=...)` | `BaseAgent(BaseAgentConfig(input_schema=In, output_schema=Out, ...))` |
| `AgentConfig`                      | `BaseAgentConfig`                       |
| `ChatHistory`                      | `AgentMemory`                           |
| `from atomic_agents import ...`    | `from atomic_agents.agents.base_agent import ...` |
| `from atomic_agents.context import SystemPromptGenerator, ChatHistory, BaseDynamicContextProvider` | `from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator, SystemPromptContextProviderBase`<br>`from atomic_agents.lib.components.agent_memory import AgentMemory` |
| `from atomic_agents.connectors.mcp import fetch_mcp_tools_async, MCPTransportType` | `from atomic_agents.lib.factories.mcp_tool_factory import MCPToolFactory` |
| `agent.run_stream(x)`              | not available — use `run_async` and accumulate |
| `agent.run_async_stream(x)`        | `agent.run_async(x)` (already streams partials) |
| `BaseDynamicContextProvider`       | `SystemPromptContextProviderBase`       |

Every pattern (orchestration, tools-don't-auto-invoke, schema chaining, context providers) is identical in spirit between v1 and v2 — only names changed.

## Repo-specific note (rethinking_prompting)

This skill lives in a research repo about prompting strategies under majority voting (paper: *Rethinking the Role of Prompting Strategies in LLM Test-Time Scaling*, ACL 2025). When a request asks for new strategy code here:

- Default to **CoT + majority voting** (the template in `PROMPT.md`, N≈16, temperature≈0.7) — the paper's headline result is that this beats more complex strategies at scale.
- Map strategy templates → `SystemPromptGenerator`; the LLM wrapper in `model.py` → the `instructor`-wrapped `client`; dataset rows → input schemas; `\boxed{...}` extraction → an output-schema field; majority voting → a caller-side `Counter.most_common(1)` loop *outside* the agent.
- For iterative strategies in the codebase — **ToT, S-RF, MAD** — use the orchestration patterns above (supervisor for S-RF; parallel + judge agent for MAD; expander + evaluator for ToT). Reuse the strategy identifiers `DiP`, `CoT`, `L2M`, `SBP`, `AnP`, `ToT`, `S-RF`, `MAD` already used in `prompts/` and `scripts/`.
- Don't add multi-agent debate or tree branching to "improve" a task unless the user explicitly asks — the paper shows complexity usually hurts at scale.
