# Setup & Testing Guide

## Prerequisites

Install `uv` (fast Python package manager):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Project Setup

Clone and initialize the atomic-agents project:

```bash
git clone https://github.com/BrainBlend-AI/atomic-agents.git
cd atomic-agents
```

## Install Dependencies

```bash
uv sync --all-packages
```

## Run Tests with Coverage

```bash
uv run pytest --cov=atomic_agents atomic-agents
```

This runs the full test suite with code coverage reporting for the `atomic_agents` module.
