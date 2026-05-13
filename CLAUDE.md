# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research framework for studying prompting strategies in Large Language Models (LLMs) at test-time scaling, published at ACL 2025 (Outstanding Paper Award). The codebase evaluates how different reasoning strategies perform under majority voting with multiple model samples.

**Key Research Finding**: Simple Chain-of-Thought (CoT) gradually dominates more complex strategies as sampling increases, due to fundamental probability distribution properties of model outputs.

## Architecture

### Core Pipeline
The inference pipeline is orchestrated through:
1. **dataset.py** → Dataset loading and prompt creation (dataset-specific)
2. **main.py** → Reasoning strategy orchestration (DiP, CoT, L2M, SBP, AnP, S-RF, ToT, MAD)
3. **model.py** → LLM inference backend abstraction (vllm, OpenAI, Gemini)

### Data Flow
```
args → create_prompt(args) → [question strings]
     → get_messages(args) → [message dicts for API]
     → LLM_generate(args) → [model outputs with tokens]
     → parse_answer(output) → [extracted answers]
     → majority voting → final answer
```

### Prompt System
Dataset-specific prompts are defined in `prompts/{DATASET}.py`. Each dataset module exports:
- `prompt_format`: Answer format instruction (boxed notation for math, letter choice for MC)
- `directly_answer`: Direct prompting (DiP) template
- `io`, `io_briefly`: Input-output templates
- `cot_pre`, `cot_0_shot`: Chain-of-Thought templates with optional exemplars

Prompt creation handles:
- Answer format auto-detection (\\boxed{} for symbolic, single letter for MC, etc.)
- Few-shot exemplar injection (`{exemplars}` placeholder in PROMPT.md)
- Dataset-specific formatting quirks (GPQA shuffles multiple-choice options; GSM-Hard expects potentially negative/nonsense results)

### Reasoning Strategies
Each strategy has distinct control flow in main.py:
- **Non-Iterative**: DiP, CoT, L2M, SBP, AnP—single forward pass with template variations
- **Iterative**: S-RF (self-refine feedback→improve cycle), ToT (tree expansion with evaluation), MAD (multi-agent debate)
- **Special**: ToT requires solution parsing; S-RF uses ThreadPoolExecutor for concurrent feedback/refinement

### Model Backends
`model.py` provides three backends via load_model(args) + LLM_generate(args):
- **vllm**: Local models via VLLM server (HuggingFace models)
- **OpenAI**: API-based (GPT-3.5, GPT-4o-mini, etc.)
- **Gemini**: Google Gemini API

Each backend returns records with `.output` (text) and `.usage` (token counts, timing).

### Evaluation
- **eval_csv_N.py**: Accuracy vs. number of samples (majority voting with N={1,4,8,16,32,...})
- **eval_csv_cost.py**: Accuracy vs. computational cost in millions of tokens
- Both scripts extract answers via `parse_answer()` and apply majority voting via `find_most_common_elements()`

## Common Commands

### Setup
```bash
pip install -r requirements.txt
# Update base_path in dataset.py and hf_token in main.py
```

### Single Inference Run
```bash
# CoT on GSM8K with gpt-4o-mini, 16 samples
python main.py \
  --model_name gpt-4o-mini \
  --model_type openai \
  --dataset GSM8K \
  --reasoning CoT \
  --shot 0 \
  --num 16 \
  --split test \
  --range_begin 0 \
  --range_end 100 \
  --openai_api_key sk-... \
  --batchsize 10

# With local vllm model
python main.py \
  --model_name Qwen/Qwen2.5-7B-Instruct \
  --model_type vllm \
  --dataset MATH \
  --reasoning ToT \
  --num 8 \
  --split test

# With Gemini
python main.py \
  --model_name gemini-1.5-flash \
  --model_type gemini \
  --dataset GPQA \
  --reasoning S-RF \
  --num 4 \
  --gemini_api_key XXXXXX
```

### Run Batch Experiments
```bash
# Pre-configured for Qwen (local) or GPT/Gemini (API)
bash scripts/Qwen_GSM8K.sh
bash scripts/GPT_GSM8K.sh
bash scripts/Gemini_GSM8K.sh
```

### Evaluation & Visualization
```bash
# Generate accuracy-vs-samples curve (Figure 1 in paper)
python eval_csv_N.py --model_name gpt-4o-mini --dataset GSM8K

# Generate accuracy-vs-cost curve (Figure 2 in paper)
python eval_csv_cost.py --model_name gpt-4o-mini --dataset GSM8K
```

## Key Parameters & Concepts

### Main Arguments
- `--model_name`: Model identifier (gpt-4o-mini, gemini-1.5-flash, Qwen/Qwen2.5-7B-Instruct, etc.)
- `--model_type`: vllm, openai, or gemini
- `--dataset`: GSM8K, GSM-Hard, MATH, GPQA, MMLU-{subject}, AIME_2024
- `--reasoning`: DiP, CoT, L2M, SBP, AnP, S-RF (rounds=1-3 by default), ToT, MAD
- `--num`: Samples per question (majority voting requires N≥2, typical N=4-32)
- `--shot`: Few-shot exemplars (0 or 1; exemplar data hardcoded in prompts/*.py)
- `--split`: test or train (dataset-dependent availability)
- `--range_begin`, `--range_end`: Question index slice (for parallel runs)
- `--batchsize`: Concurrent requests per batch
- `--max_num_workers`: ThreadPoolExecutor worker count
- `--verbose` / `--verbal`: Print prompts and outputs for debugging

### Answer Extraction
- **Mathematical (GSM8K, MATH, AIME)**: Extracts \\boxed{...} and numerically compares
- **Multiple-Choice (GPQA, MMLU)**: Expects single capital letter (A/B/C/D)
- **GSM-Hard**: Allows negative/nonsense results (unlike GSM8K)
- Majority voting picks mode; ties broken randomly

### Theory Insights
- "Easy" questions: mode of answer distribution is correct—accuracy increases with N
- "Hard" questions: distribution has multiple peaks—accuracy decreases with N
- Simple strategies (CoT) have uniform answer distribution → better long-tail scaling
- Complex strategies (ToT, MAD) produce bimodal distributions → dominate at small N but plateau/degrade at large N

## Debugging & Development Notes

### Extending Prompts
1. Edit `prompts/{DATASET}.py` to add/modify templates
2. Update `create_prompt()` in dataset.py if new template variables needed
3. Test with small `--range_end` (e.g., 5) to verify format before large runs

### Adding New Datasets
1. Create `prompts/NEWDATASET.py` with `prompt_format`, `cot_0_shot`, etc.
2. Add loader in `dataset.read_dataset()` using `load_dataset()` or custom code
3. Implement answer parser in `dataset.examine_output()` (numerical, letter, etc.)
4. Add dataset name to shell script templates

### Debugging Model Calls
- Set `--verbal` to print full prompts and raw outputs
- Check `logs/` directory for saved JSON responses (if logging enabled)
- Gemini safety filters may block some outputs—warnings appear in console

### Cost Estimation
Cost function in dataset.py (`get_cost()`) uses:
- Gemini: 0.075M⁻¹ (prompt), 0.3M⁻¹ (completion) [millions of tokens]
- GPT-4o-mini: 0.15M⁻¹ (prompt), 0.6M⁻¹ (completion)
- Default fallback: 0.15M⁻¹ / 0.6M⁻¹

## Repository Layout
```
main.py              # Inference orchestration & prompting strategy logic
model.py             # LLM backend abstraction (vllm, OpenAI, Gemini)
dataset.py           # Dataset loading & prompt creation & evaluation utilities
eval_csv_N.py        # Accuracy vs. sample count
eval_csv_cost.py     # Accuracy vs. computational cost
prompts/             # Dataset-specific prompt templates (6 datasets)
scripts/             # Example shell scripts (Qwen, GPT, Gemini)
PROMPT.md            # Reference prompt template with CoT + majority voting instructions
README.md            # Full project documentation with citations & setup
```
