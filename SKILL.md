---
name: cavans-context7-integration
description: |
  Orchestrates creative output via Cavans Art and validates technical implementation
  using Context7 live documentation. Ensures generated code or visual logic is both
  aesthetically sound and technically up-to-date.

  AUTO-TRIGGER when the user:
  - mentions "Cavans", "Cavans Art", "canvas art", or asks for visual/diagram generation
  - mentions "Context7", "ctx7", or says "use context7" in a prompt
  - asks for a Mermaid diagram, SVG illustration, or annotated visual artifact
  - requests live/up-to-date library documentation, API reference lookups, or
    version-specific docs for a framework, SDK, or CLI
  - combines a creative request with a need for authoritative documentation
    (e.g. "draw the architecture for the latest Next.js app router")

  SKIP when the request is a pure refactor, business-logic debugging, or general
  programming that needs neither visual output nor live docs.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - WebFetch
---

# Cavans Art & Context7 Integration

## Description
This skill orchestrates creative output via **Cavans Art** and validates technical
implementation using **Context7** live documentation. It ensures that any code or
visual logic generated is both aesthetically sound and technically up-to-date.

## Logic Flow (Myrimaids Graph)
```mermaid
graph TD
    User([User Prompt]) --> Router{Identify Intent}
    Router -- "Creative/Visual" --> CA[Cavans Art Engine]
    Router -- "Docs/Reference" --> C7[Context7 Referee]

    C7 -- "use context7" --> Fetch[Live Documentation]
    Fetch --> CA

    CA --> Artifact[Mermaid/SVG/Code]
    Artifact --> Output([Final Response])

    subgraph "Context7 Sub-Commands"
        C7 --> Lib[ctx7 library]
        C7 --> Doc[ctx7 docs]
    end
```

## Auto-Trigger Patterns

The skill activates automatically (no explicit `/skill` invocation required) on:

| Trigger Phrase / Pattern              | Routed To           |
| ------------------------------------- | ------------------- |
| `use context7`                        | Context7 Referee    |
| `ctx7 library <name>`                 | Context7 → Lib      |
| `ctx7 docs <topic>`                   | Context7 → Doc      |
| `draw …`, `diagram …`, `visualize …`  | Cavans Art Engine   |
| `mermaid …`, `svg …`, `flowchart …`   | Cavans Art Engine   |
| Creative request + library reference  | C7 → CA pipeline    |

## Sub-Commands

- **`ctx7 library <name>`** — resolve a library identifier and load its current
  documentation surface.
- **`ctx7 docs <topic>`** — fetch focused documentation pages for a specific topic
  or API.
- **`cavans render <spec>`** — produce a Mermaid, SVG, or annotated code artifact
  from a structured spec.

## Workflow

1. **Identify intent** — classify the prompt as Creative/Visual, Docs/Reference,
   or a combination.
2. **Fetch references first** — if docs are needed, run Context7 lookups before
   generating any artifact so the output reflects current APIs.
3. **Generate the artifact** — hand the validated references to the Cavans Art
   Engine to produce the visual or code output.
4. **Return the final response** — include the artifact plus a short note on
   which doc versions were consulted.
