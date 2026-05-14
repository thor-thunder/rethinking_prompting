# CLAUDE.md: Rethinking Prompting Strategies in LLM Test-Time Scaling

## Project Overview

This is an ACL 2025 Outstanding Paper Award research project that investigates how different prompting strategies perform as you scale test-time computation for Large Language Models (LLMs). The key finding: simple Chain-of-Thought (CoT) and Direct Prompting (DiP) often outperform complex strategies like Tree-of-Thoughts or Multi-Agent Debate when using majority voting with larger sample sizes.

**Key Resources:**
- Paper: https://arxiv.org/abs/2505.10981
- ACL 2025: https://aclanthology.org/2025.acl-long.1356/
- GitHub: https://github.com/thor-thunder/rethinking_prompting

## Repository Structure

```
rethinking_prompting/
├── main.py                 # Entry point for inference pipeline
├── model.py                # LLM backend implementations (OpenAI, Gemini, vLLM)
├── dataset.py              # Dataset loading, parsing, and evaluation utilities
├── eval_csv_N.py           # Evaluation by sampling time (majority voting)
├── eval_csv_cost.py        # Evaluation by computational cost
├── PROMPT.md               # Universal prompt template documentation
├── prompts/                # Dataset-specific prompt definitions
│   ├── GSM8K.py            # Grade School Math 8K (arithmetic word problems)
│   ├── GSM_Hard.py         # GSM-Hard (difficult variants)
│   ├── MATH.py             # MATH dataset (competition math)
│   ├── AIME.py             # AIME 2024 (advanced competition math)
│   ├── GPQA.py             # GPQA (expert-level scientific QA)
│   └── MMLU.py             # MMLU (broad knowledge assessment)
├── scripts/                # Shell scripts for running predefined experiments
│   ├── Qwen_GSM8K.sh       # Qwen2.5-7B-Instruct on GSM8K example
│   ├── Qwen_MATH.sh        # Qwen2.5-7B-Instruct on MATH example
│   ├── GPT_GSM8K.sh        # GPT models on GSM8K
│   └── Gemini_GSM8K.sh     # Gemini models on GSM8K
└── requirements.txt        # Python dependencies

```

## Core Modules

### main.py: Inference Pipeline

Orchestrates the full inference workflow for different prompting strategies.

**Key Functions:**
- `get_model_outputs(args)`: Routes to strategy-specific logic
- Handles reasoning strategies: DiP, CoT, AnP, L2M, S-RF, ToT, SBP, MAD
- Manages message passing for multi-turn strategies
- Supports thread pooling for parallel refinement rounds

**Supported Reasoning Strategies:**
1. **Non-Iterative** (single-pass):
   - `DiP`: Direct Prompting (no reasoning)
   - `CoT`: Chain-of-Thought (step-by-step reasoning)
   - `L2M`: Least-to-Most Prompting
   - `SBP`: Step-Back Prompting
   - `AnP`: Analogous Prompting

2. **Iterative** (multi-pass with refinement):
   - `ToT`: Tree-of-Thoughts (explores multiple solution paths)
   - `S-RF`: Self-Refine (feedback → improve → refine cycles)
   - `MAD`: Multi-Agent Debate (agent disagreement resolution)

**Args Structure** (used throughout):
- `args.reasoning`: Strategy name
- `args.model_name`: Model identifier
- `args.dataset`: Dataset name (GSM8K, MATH, GPQA, etc.)
- `args.num`: Samples per question (for majority voting)
- `args.rounds`: Refinement rounds (for iterative strategies)
- `args.messages`: Multi-turn conversation history
- `args.query`: Single-turn prompt(s)
- `args.verbal`: Debug flag for printing prompts

### model.py: LLM Backend Integration

Implements inference interfaces for multiple LLM providers.

**Key Classes:**
- `Gemini`: Google Gemini API with safety settings
- `OpenAI`: OpenAI API client (GPT-3.5, GPT-4o)
- vLLM support via `model.py` (local inference)

**Key Functions:**
- `load_model(args)`: Factory to instantiate the right backend
- `LLM_generate(args)`: Unified inference interface returning structured records
- `get_messages(args)`: Converts internal message format to provider-specific format

**Response Format:**
Returns list of lists: `[[{record1}, {record2}, ...], ...]`
- Each inner list = one question's samples
- Each record dict contains:
  - `output`: Generated text
  - `prompt_tokens`: Input tokens
  - `completion_tokens`: Output tokens
  - Reasoning-specific fields (`output0`, `problems`, etc. for S-RF/ToT/etc.)

### dataset.py: Data Management & Evaluation

Handles dataset loading, prompt creation, answer parsing, and evaluation metrics.

**Key Functions:**
- `read_dataset(args)`: Loads dataset from HuggingFace
- `create_prompt(args)`: Constructs prompts using strategy-specific templates
- `parse_answer(...)`: Extracts final answer from model output (regex-based)
- `parse_best_solution(...)`: Extracts reasoning steps for eval
- `get_unique_most_common_answer(outputs)`: Majority voting
- `get_cost(model_name, prompt_tokens, completion_tokens)`: Token-to-cost conversion

**Supported Datasets:**
- **Math:** GSM8K, GSM-Hard, MATH, AIME
- **Science:** GPQA, MMLU (with domain subsets)
- **Format:** Auto-detection of answer type (number, expression, letter, text)

**Dataset Splits:**
- Most use HuggingFace datasets library
- GSM-Hard from `reasoning-machines/gsm-hard`
- GPQA from `Idavidrein/gpqa` with answer shuffling
- MMLU splits by domain (high_school_physics, etc.)

**Path Configuration:**
- `base_path`: Must be set in `dataset.py` to your repo root
- `log_path`: Auto-derived from `base_path`
- Output logs stored as JSON per experiment

### eval_csv_N.py & eval_csv_cost.py: Evaluation Scripts

Compute accuracy curves for majority voting.

**eval_csv_N.py** (Sampling Time Budget):
- X-axis: Number of samples (N)
- Y-axis: Accuracy at that N
- Computes: accuracy @ N=1,2,3,...,max_samples
- Usage: `python eval_csv_N.py --model_name "qwen2.5-7b-instruct" --dataset "GSM8K"`

**eval_csv_cost.py** (Computation Cost Budget):
- X-axis: Cost ($) based on token pricing
- Y-axis: Accuracy at that cost
- Pricing: `get_cost()` maps model + tokens → USD
- Same command interface as eval_csv_N

**Output:** CSV files with columns [N/Cost, Accuracy] for plotting.

### prompts/: Strategy-Specific Prompt Templates

Each dataset has a module defining prompt templates for all strategies.

**File Structure Example (prompts/GSM8K.py):**
```python
prompt_format = "Your final answer should be \\boxed{answer}"
cot_0_shot = "..." # CoT with no examples
cot_1_shot = "..." # CoT with 1 example
directly_answer = "..." # DiP template
tot_prompt = "..." # Tree-of-Thoughts prompt
sbp_prompt = "..." # Step-Back Prompting
# ... strategy templates
```

**Placeholders:**
- `{question}`: Substituted with actual question
- `{exemplars}`: Few-shot examples (optional)
- `{choices}`: Multiple choice options (for MMLU/GPQA)

**Key Pattern:** Each strategy has separate templates optimized for that reasoning style.

## Development Workflows

### Running Experiments

**Quick Start (Using Shell Script):**
```bash
bash scripts/Qwen_GSM8K.sh
```

**Manual Run (Full Control):**
```bash
python main.py \
  --model_name "qwen2.5-7b-instruct" \
  --dataset "GSM8K" \
  --reasoning "CoT" \
  --num 16 \
  --split "test"
```

**Typical Args:**
- `--model_name`: Model identifier (qwen2.5-7b-instruct, gpt-4o-mini, gemini-1.5-flash)
- `--dataset`: One of GSM8K, GSM-Hard, MATH, AIME, GPQA, MMLU-[domain]
- `--reasoning`: Strategy (DiP, CoT, L2M, SBP, AnP, ToT, S-RF, MAD)
- `--num`: Samples per question for majority voting (typically 8-32)
- `--rounds`: Refinement rounds for iterative strategies (default 2 for S-RF)
- `--split`: "test" or "train"
- `--seed`: Random seed for reproducibility
- `--verbose` / `--verbal`: Debug printing

### Evaluation Workflow

1. **Run inference** with `main.py` → generates logs with outputs & token counts
2. **Compute accuracy curve** with `eval_csv_N.py` or `eval_csv_cost.py`
3. **Plot results** (user responsibility, tools accept CSV output)

### Adding a New Dataset

1. Create `prompts/NEWDATASET.py` with templates for each strategy
2. Add loading logic in `dataset.py`:
   ```python
   elif dataset == "NEWDATASET":
       ds = load_dataset("hf_path/newdataset")[args.split]
       dataset_list = [d for d in ds]
   ```
3. Add parsing function: `parse_answer_NEWDATASET(...)`
4. Test with: `python main.py --dataset NEWDATASET --reasoning CoT --num 1`

### Adding a New LLM Provider

1. Create class in `model.py` (inherit from base if exists)
2. Implement `get_response(messages, n=1)` returning list of `{"output": str, "prompt_tokens": int, "completion_tokens": int}`
3. Update `load_model(args)` factory to instantiate your class
4. Test: `python main.py --model_name "your-model" --dataset GSM8K --num 1`

## Configuration & Setup

### API Keys & Credentials

**Before first run:**
1. **HuggingFace:** Set `hf_token` in `main.py` (line 13)
   - Required for gated models (e.g., Llama)
   - Get token: https://huggingface.co/settings/tokens

2. **OpenAI:** Set environment variable `OPENAI_API_KEY`
   - or in `model.py` constructor

3. **Google Gemini:** Set environment variable `GOOGLE_API_KEY`
   - or pass to `Gemini()` class

4. **vLLM (Local):** Requires running vLLM server
   - `python -m vllm.entrypoints.openai.api_server --model qwen2.5-7b-instruct`
   - Models run locally, no API key needed

### Path Configuration

Edit `dataset.py` line 11:
```python
base_path = "/your/path/to/rethinking_prompting"
```
This must point to the repository root.

### Requirements

All dependencies in `requirements.txt`:
- `openai`: OpenAI API client
- `google-generativeai`: Google Gemini API
- `vllm`: Local LLM inference
- `datasets`: HuggingFace dataset loading
- `numpy`, `pyarrow`, `multiprocess`: Data processing
- `matplotlib`, `openpyxl`: Visualization & export

Install with: `pip install -r requirements.txt`

## Key Conventions

### Naming & Structure

**Model Names:**
- vLLM: model_name exact string (e.g., "qwen2.5-7b-instruct")
- OpenAI: "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"
- Gemini: "gemini-1.5-flash", "gemini-2.0-flash"

**Dataset Names:**
- Exact match: "GSM8K", "MATH", "AIME", "GPQA"
- Variants: "GSM-Hard"
- MMLU subsets: "MMLU-high_school_physics", etc.

**Reasoning Strategy Names (case-sensitive):**
- Non-iterative: "DiP", "CoT", "L2M", "SBP", "AnP"
- Iterative: "ToT", "S-RF", "MAD"

### Answer Extraction

**Pattern:** Model outputs must end with `\boxed{answer}`
- Regex: `r'\\boxed\{([^}]*)\}'`
- For multi-choice: Letter only (A-D)
- For math: Number or expression
- For GPQA: Letter (auto-shuffled choices)

**Missing/Invalid Answers:** Treated as `None`, excluded from majority voting

### Output Format

Inference logs stored as JSON:
- Path: `{base_path}/logs/{model_name}_{dataset}_{reasoning}_{num}_{timestamp}.json`
- Each entry: `{question, reasoning_type, outputs: [...]}`
- Each output: `{output_text, prompt_tokens, completion_tokens, ...}`

## Testing & Validation

**Quick Sanity Check:**
```bash
python main.py --model_name "gpt-3.5-turbo" --dataset "GSM8K" --reasoning "CoT" --num 2 --split "test"
```
Should complete in < 1 minute, print sample question/answer.

**Validate Parsing:**
```python
from dataset import parse_answer
assert parse_answer("The answer is \\boxed{42}") == "42"
```

**Check Token Counting:**
- Model classes must accurately report prompt_tokens and completion_tokens
- Cost conversion: `get_cost(model_name, prompt_tokens, completion_tokens)`

## Common Patterns & Idioms

### Multi-Turn Message Building (for S-RF, ToT, MAD)

```python
args.messages = [[initial_query]]  # Start with single query
# ... get model response ...
args.messages[0].append(response)  # Add to conversation
args.messages[0].append(next_prompt)  # Add follow-up
# ... get refined response ...
```

### Thread Pooling for Parallel Refinement

```python
with ThreadPoolExecutor(max_workers=5) as executor:
    executor.submit(concat_refine_messages, messages, output)
    executor.submit(concat_refine_records, records, output, field_name)
```
Used in S-RF to parallelize message updates across questions.

### Majority Voting

```python
from dataset import get_unique_most_common_answer
best_answer = get_unique_most_common_answer([output1, output2, output3])
```
Handles ties by random choice among tied answers.

## Git Workflows & Branch Strategy

**Main Branch:** `main`
- Stable, released code
- ACL 2025 paper version pinned here

**Feature Branches:**
- `claude/add-claude-documentation-9ZT0F`: Current documentation branch
- Format: `claude/<feature-description>-<ticket-id>`

**Commit Conventions:**
- Descriptive messages starting with verb: "Add", "Update", "Fix"
- Examples: "Add CLAUDE.md documentation", "Update eval_csv_N.py with new metrics"

## Helpful Tips for AI Assistants

### Understanding Experimental Results
- **key metric:** accuracy @ different sample counts (eval_csv_N.py) or costs (eval_csv_cost.py)
- Majority voting with N samples often beats complex single-sample strategies
- Simple CoT scales better than ToT/MAD as N increases

### Debugging Failed Runs
1. Check `base_path` and `hf_token` in configuration
2. Verify API keys in environment variables
3. Test with `--num 1` first (single sample is faster)
4. Use `--verbose` flag to see actual prompts and responses

### Performance Tuning
- vLLM is fastest (local), but requires GPU
- OpenAI/Gemini are slower but don't need hardware
- Batch processing: Can optimize `LLM_generate()` to parallelize API calls
- Token caching: Not yet implemented, but could reduce cost for repeated queries

### Paper Connection
- Results support using CoT + majority voting over complex strategies
- "Disturbed peaks" theory explains why complex strategies regress with scale
- Adaptive sampling by question difficulty is implemented but not in main release

## References

- **Paper:** "Rethinking the Role of Prompting Strategies in LLM Test-Time Scaling" (Liu et al., 2025)
- **ArXiv:** https://arxiv.org/abs/2505.10981
- **ACL:** https://aclanthology.org/2025.acl-long.1356/
- **Datasets:** All loaded from HuggingFace Hub
- **Models:** OpenAI, Google Gemini, vLLM (Hugging Face models)

---

**Last Updated:** 2026-05-14
**Maintained by:** Original authors + community contributions
