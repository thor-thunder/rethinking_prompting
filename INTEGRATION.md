# Integration with Atomic Agents

> ⚠️ **Start with [CLAUDE.md](CLAUDE.md) for quick navigation and essential commands**

This document provides detailed integration information between `rethinking_prompting` and the `atomic-agents` framework.

## Project Structure

```
/
├── rethinking_prompting/        # Main project
│   ├── model.py                # LLM interfaces
│   ├── dataset.py             # Data loading and processing
│   ├── main.py                # Orchestration logic
│   ├── tests/                 # Test suite (59 tests, 38% coverage)
│   ├── pyproject.toml         # Project configuration
│   └── requirements.txt       # Dependencies
│
└── atomic-agents/             # Agent framework (sibling project)
    ├── atomic-agents/         # Core framework
    ├── atomic-assembler/      # Agent assembly tools
    ├── atomic-examples/       # Example implementations
    └── atomic-forge/          # Tool forge
```

## Running Tests

### All dataset tests
```bash
python -m pytest tests/unit/test_dataset.py -v
```

### With coverage report
```bash
python -m pytest tests/unit/test_dataset.py --cov=dataset --cov-report=html
```

### Specific test class
```bash
python -m pytest tests/unit/test_dataset.py::TestParseAnswerGSM8K -v
```

## Test Coverage Summary

**Current Coverage:** 38% of `dataset.py` (59 tests)

### Tested Functions
- ✅ `parse_answer()` - All 6 datasets (GSM8K, GSM-Hard, GPQA, MMLU, MATH, AIME)
- ✅ `examine_output()` - Evaluation metrics validation
- ✅ `get_cost()` - Cost calculation for all model types
- ✅ `find_most_common_elements()` - Majority voting
- ✅ `get_unique_most_common_answer()` - Answer aggregation
- ✅ `parse_best_solution()` - Tree of Thoughts selection
- ✅ `last_boxed_only_string()` - LaTeX parsing
- ✅ `remove_boxed()` - Box extraction
- ✅ `is_equiv()` - Mathematical equivalence

## Using with Atomic Agents

To use `atomic-agents` with `rethinking_prompting`:

```python
from atomic_agents.agents import Agent
from rethinking_prompting.model import load_model

# Load a model
load_model(args)

# Create an Atomic Agent
agent = Agent(...)

# Run inference
response = agent.run(...)
```

## Next Steps

### Phase 2 Testing
- Dataset loading tests for all 6 datasets
- API response parsing tests
- Majority voting integration tests
- Error handling tests

### Phase 3 Testing  
- End-to-end pipeline tests
- Multi-strategy comparison tests
- Performance regression tests

## Dependencies

### Core
- `datasets>=3.2.0` - Dataset loading
- `openai>=1.53.0` - OpenAI API
- `google-generativeai>=0.7.2` - Gemini API
- `vllm>=0.8.4` - Local model inference
- `numpy>=1.26.4` - Numerical computing

### Testing
- `pytest>=7.0` - Test framework
- `pytest-cov>=4.0` - Coverage tracking
- `pytest-mock>=3.10` - Mocking utilities

## Configuration

### Environment Variables

Set these in your shell or `.env` file:

```bash
# OpenAI
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Google Gemini
export GOOGLE_API_KEY="your-key"

# HuggingFace
export HF_TOKEN="your-token"
```

## Troubleshooting

### uv not found
Reinstall uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Import errors
Ensure dependencies are installed:
```bash
uv pip install -r requirements.txt
pip install -e .
```

### Tests failing
Check Python version (requires 3.11+):
```bash
python --version
```

## Resources

- [rethinking_prompting Paper](https://arxiv.org/abs/2505.10981)
- [atomic-agents README](../atomic-agents/README.md)
- [uv Documentation](https://docs.astral.sh/uv/)
