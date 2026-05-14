# Claude Code Guide: Rethinking Prompting

Quick navigation for Claude Code sessions. **Start here.**

## 🎯 What This Project Does

Research codebase analyzing LLM test-time scaling with multiple prompting strategies (CoT, ToT, Self-Refine, etc.) across 6 benchmarks. See [readme.md](readme.md) for the research paper.

## 📋 Essential Commands

### Run Tests (Phase 1: 59 tests, 38% coverage)
```bash
./run_tests.sh --all              # Full test suite with coverage
./run_tests.sh --fast             # Quick tests (no coverage)
./run_tests.sh --coverage         # Generate HTML report in htmlcov/
python -m pytest tests/unit/test_dataset.py -v
```

### Setup Environment
```bash
# First time setup
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv pip install -r requirements.txt

# Run with uv
uv run pytest tests/unit/test_dataset.py -v
```

## 📂 Key Files & Structure

| File | Purpose |
|------|---------|
| **model.py** | LLM interfaces (vLLM, OpenAI, Gemini) |
| **dataset.py** | Dataset loading, answer parsing, cost calculation |
| **main.py** | Orchestration & prompting strategy execution |
| **tests/unit/test_dataset.py** | 59 unit tests (parse_answer, costs, evaluation) |
| **pyproject.toml** | Project config, test dependencies, uv integration |
| **INTEGRATION.md** | Setup, dependencies, atomic-agents integration |
| **.gitignore** | Cache, coverage, IDE files excluded |
| **uv.lock** | Pinned dependency versions (reproducible builds) |

## 🔧 Common Tasks

### Add More Tests (Phase 2/3)
- **Phase 2:** Dataset loading, API parsing, majority voting
- **Phase 3:** End-to-end pipelines, regressions

See [INTEGRATION.md → Next Steps](INTEGRATION.md#next-steps)

### Check Test Coverage
```bash
./run_tests.sh --coverage
open htmlcov/index.html
```

### Debug a Test
```bash
python -m pytest tests/unit/test_dataset.py::TestParseAnswerGSM8K::test_parse_boxed_answer -vv
```

### View Test Output
- **Parsing tests:** `tests/unit/test_dataset.py::TestParseAnswer*`
- **Cost tests:** `tests/unit/test_dataset.py::TestGetCost`
- **Evaluation:** `tests/unit/test_dataset.py::TestExamineOutput`

## 📊 Current Status

✅ **Phase 1 Complete**
- 59 tests covering critical functions
- 38% dataset.py coverage
- All datasets validated (GSM8K, GSM-Hard, GPQA, MMLU, MATH, AIME)

⏳ **Phase 2/3 Pending**
- Dataset loading tests
- API error handling
- End-to-end pipeline tests

## 🤖 Integration: atomic-agents

The `atomic-agents/` sibling project is available as a framework. See full setup in [INTEGRATION.md → Integration with Atomic Agents](INTEGRATION.md#using-with-atomic-agents).

```bash
cd /path/to/atomic-agents
uv sync --all-packages
```

## 🔗 Documentation Links

- **Research Paper:** [arxiv.org/abs/2505.10981](https://arxiv.org/abs/2505.10981)
- **Setup & Architecture:** [INTEGRATION.md](INTEGRATION.md)
- **Test Runner:** [run_tests.sh](run_tests.sh)
- **Original README:** [readme.md](readme.md)

## ⚡ Tips for Claude Sessions

### Before Starting Work
```bash
git status                           # Check branch
python -m pytest tests/ -v --tb=short  # Verify tests pass
```

### When Done
```bash
git add <files>
git commit -m "Change description

Details about what was changed and why.

https://claude.ai/code/session_XXXXX"
git push -u origin <branch>
```

### Coverage Goal
Target is **50%+ coverage** of critical paths (dataset.py, model.py). Focus on:
- Answer parsing edge cases
- Cost calculations (must be exact)
- Dataset-specific validation
- Error handling

## 🐛 Troubleshooting

**Tests fail with import errors:**
```bash
uv pip install -r requirements.txt
```

**uv not found:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Tests pass locally but CI fails:**
Check `uv.lock` is committed and Python version is 3.11+

## 📝 Notes

- Tests use pytest fixtures in `tests/conftest.py`
- Mock LLM responses for testing without API calls
- All tests are deterministic (use fixed seeds where needed)
- Code style: Follow existing patterns in dataset.py/model.py

---

**Last Updated:** 2025-05-14  
**Test Status:** ✅ 59/59 passing  
**Coverage:** 38% (dataset.py)
