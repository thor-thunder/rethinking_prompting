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

The inference pipeline follows a carefully architected multi-stage process that transforms raw command-line arguments into statistically robust predictions through iterative model sampling and ensemble voting. Let us break down each stage in comprehensive detail:

#### Stage 1: Argument Parsing & Configuration
The pipeline begins when command-line arguments are parsed and consolidated into an `args` object. This object serves as the configuration carrier throughout the entire inference pipeline, containing critical parameters such as:
- **Model Configuration**: `model_name`, `model_type` (vllm/openai/gemini), and model-specific settings
- **Dataset Selection**: `dataset` (GSM8K/MATH/GPQA/MMLU/AIME/GSM-Hard) and `split` (train/test)
- **Reasoning Strategy**: `reasoning` strategy choice (DiP/CoT/L2M/SBP/AnP/S-RF/ToT/MAD) which fundamentally determines control flow
- **Sampling Parameters**: `num` (number of samples for majority voting), `shot` (few-shot exemplar count)
- **Execution Parameters**: `batchsize`, `max_num_workers`, `range_begin`, `range_end` for dataset slicing
- **API Credentials**: `openai_api_key`, `openai_base_url`, `gemini_api_key` depending on backend

#### Stage 2: Prompt Creation & Template Instantiation
The `create_prompt(args)` function orchestrates dataset-specific prompt engineering by:
1. **Loading Dataset Questions**: Retrieving the subset of questions from `read_dataset(args)` corresponding to the range specified in `range_begin:range_end`
2. **Selecting Template Strategy**: Based on `args.reasoning`, the function selects the appropriate prompt template architecture:
   - **DiP (Direct Prompting)**: Uses `directly_answer` template—minimal scaffolding, direct instruction
   - **CoT (Chain-of-Thought)**: Uses `cot_0_shot` or `cot_1_shot` templates with structured step-by-step reasoning frameworks
   - **L2M (Least-to-Most)**: Constructs decomposition prompts that break problems into prerequisite sub-problems
   - **SBP (Step-Back Prompting)**: Generates abstraction prompts asking "What are the underlying principles?"
   - **AnP (Analogous Prompting)**: Constructs analogy-based prompts drawing parallels to similar solved problems
   - **S-RF (Self-Refine)**: Uses iterative feedback→refinement cycles requiring special message list construction
   - **ToT (Tree of Thoughts)**: Generates evaluation and exploration prompts for tree search
   - **MAD (Multi-Agent Debate)**: Constructs debate prompts with multiple viewpoint directives
3. **Exemplar Injection**: If `shot=1`, the function injects few-shot exemplars into the `{exemplars}` placeholder within the template string
4. **Answer Format Specification**: Embeds dataset-specific answer format instructions (e.g., `\boxed{...}` for mathematical reasoning tasks, or capital letter A/B/C/D for multiple-choice)
5. **Dataset-Specific Adaptations**: Applies special formatting rules:
   - **GSM8K**: Emphasizes numerical answer extraction with decimal precision
   - **MATH**: Expects symbolic mathematical expressions in boxed notation
   - **GPQA**: Shuffles multiple-choice options and specifies capital letter output
   - **MMLU**: Specifies exact output sentence format: "The correct answer is X"
   - **AIME**: Expects integer numerical results in boxed form
   - **GSM-Hard**: Explicitly permits negative and non-sensical results despite semantic implausibility
6. **Question Substitution**: Replaces `{question}` placeholder with actual question text from dataset
7. **Output**: Returns a list of fully instantiated prompt strings, one per question in the range

#### Stage 3: Message Format Conversion & Backend Adaptation
The `get_messages(args)` function performs critical backend-specific message formatting by:
1. **Checking Backend Type**: Determines whether the target is `openai`/compatible (standard JSON message format) or `gemini` (proprietary message format)
2. **For OpenAI-Compatible Backends**:
   - Converts string prompts to message dictionaries with role/content pairs
   - If `args.system` is provided, adds system prompt as first message with role="system"
   - Alternates user/assistant roles based on message sequence position (supporting multi-turn conversations)
   - Creates structure: `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]`
3. **For Gemini Backend**:
   - Uses proprietary format with role="user"/"model" (not "user"/"assistant")
   - Message content wrapped in `{"parts": [message]}` structure
   - Omits system prompt from message list (passed separately to API)
4. **Handling Iterative Strategies**: For strategies like S-RF that build conversation history:
   - Maintains `args.messages` as list of message sequences
   - Appends feedback prompts and refinement directives to conversation history
   - Each iteration extends the conversation with new user turns and assistant responses
5. **Output**: Returns backend-compatible message list structure ready for API/model consumption

#### Stage 4: Model Inference & Token Generation
The `LLM_generate(args)` function executes actual model inference through the appropriate backend:

**For VLLM Backend (Local Models)**:
- Initializes persistent vLLM engine connection (pooled across batch)
- For each message sequence in the batch:
  - Sends complete message history through `engine.generate()` with sampling parameters
  - Generates `args.num` independent samples per question (using `num_return_sequences`)
  - Collects raw text outputs with token-level metadata
  - Records completion time and token usage statistics
- Returns list of records: each record contains `{"output": str, "usage": {...}}`

**For OpenAI Backend (API)**:
- Authenticates using `OPENAI_API_KEY` environment variable or `--openai_api_key` argument
- Constructs API request with:
  - Complete message list from Stage 3
  - `n=args.num` (number of independent completions to generate)
  - Temperature settings (typically ~0.7 for sampling variety, 0 for deterministic)
  - Top-p/top-k nucleus sampling parameters
  - Max tokens guidance
- Handles rate limiting and retry logic with exponential backoff
- Extracts responses from API return object
- Calculates token usage from `usage.prompt_tokens` and `usage.completion_tokens`
- Returns records with metadata about token consumption and latency

**For Gemini Backend (Google API)**:
- Authenticates using `GOOGLE_API_KEY`
- Calls `GenerativeModel.generate_content()` with safety settings configured
- Requests multiple candidates via `generation_config` parameter
- Handles candidate filtering (only counts successfully completed generations with finish_reason=1)
- Implements retry loops for rate limiting and transient failures
- Post-processes token counts using `.count_tokens()` API
- Returns records including usage and timing information

**For Iterative Strategies (S-RF, ToT, MAD)**:
- Executes multiple inference rounds in sequence
- Each round appends new messages to conversation history
- Subsequent inferences use complete message history (context accumulation)
- S-RF: feedback→improvement→feedback cycle requiring 2-3 inference calls per question
- ToT: multiple expansion steps followed by evaluation step to guide tree search
- MAD: parallel agent generations followed by debate round

#### Stage 5: Answer Extraction & Standardization
The `parse_answer(output)` function extracts structured answers from unstructured model outputs by:

**For Mathematical Reasoning Tasks (GSM8K, MATH, AIME)**:
- Uses regex pattern to locate `\boxed{...}` notation: `\boxed{([^}]*)}`
- Extracts content between curly braces
- For numerical comparison: removes all non-numeric characters and converts to float
- Tolerates formatting variations: `\boxed{3.14}`, `\boxed{\frac{22}{7}}`, etc.
- Returns extracted mathematical expression or numerical value

**For Multiple-Choice Tasks (GPQA, MMLU)**:
- Scans for capital letters A, B, C, or D in the output
- Uses heuristics to find the final stated answer (often at end of response)
- Handles phrases like "The correct answer is A" or standalone letter mentions
- Returns single capital letter as answer

**For GSM-Hard (Mathematical with Edge Cases)**:
- Same extraction as GSM8K but accepts negative numbers and unusual results
- Does not reject outputs based on semantic reasonableness
- Preserves decimal precision for accurate comparison

**For Unstructured Answers**:
- Falls back to extracting the most recently mentioned answer-like token
- Returns None if no structured answer detected

#### Stage 6: Majority Voting & Result Aggregation
After collecting `args.num` independent samples per question, the system performs ensemble aggregation:

1. **Answer Frequency Analysis**:
   - Counts occurrence frequency of each unique answer across the `num` samples
   - Uses Python `Counter` data structure for efficient frequency calculation
   - Handles None/null answers (filtered out before voting)

2. **Mode Selection**:
   - Identifies the answer(s) with maximum frequency (could be ties)
   - Uses `find_most_common_elements()` to find all tied maximum-frequency answers
   - Returns `(most_common_elements_list, max_count)` tuple

3. **Tie-Breaking**:
   - If multiple answers tie for maximum frequency, randomly selects one
   - Ensures deterministic behavior across runs through seeding when desired
   - Uses `get_unique_most_common_answer()` for single-answer output

4. **Accuracy Comparison**:
   - Extracted answer compared against ground truth using `examine_output()`
   - Numerical tasks: float comparison with tolerance of 1e-4
   - Multiple-choice: exact letter matching
   - Returns binary correct/incorrect classification

5. **Aggregation Across Dataset**:
   - Accumulates accuracy scores across all questions
   - Calculates `accuracy = correct_count / total_count`
   - Records per-question metadata: answer, confidence (max_count/num), tokens used

6. **Output**:
   - Returns comprehensive record structure with predictions, confidences, and token statistics
   - Enables downstream analysis of scaling behavior and strategy performance

#### Complete Pipeline Visualization
```
args (model, dataset, strategy, num=N)
  ↓
[Q1, Q2, ..., Qn] ← read_dataset()
  ↓
create_prompt(args) → [prompt_1, ..., prompt_n]
  ↓
get_messages(args) → [msgs_1, ..., msgs_n] (backend-adapted)
  ↓
LLM_generate(args) → [[output_1_1, ..., output_1_N],    ← N samples per question
                       [output_2_1, ..., output_2_N],
                       ...
                       [output_n_1, ..., output_n_N]]
  ↓
parse_answer() → [[ans_1_1, ..., ans_1_N],
                   [ans_2_1, ..., ans_2_N],
                   ...
                   [ans_n_1, ..., ans_n_N]]
  ↓
majority_voting() → [ans_1_mode, ans_2_mode, ..., ans_n_mode]
  ↓
examine_output(ans_i, ground_truth_i) → [correct_1, correct_2, ..., correct_n]
  ↓
accuracy = sum(correct_i) / n
```

#### Token Accounting Throughout Pipeline
Each stage consumes and produces tokens according to its computation:
- **Stage 2 (Prompt Creation)**: Minimal tokens (prompt assembly, no model calls)
- **Stage 3 (Message Formatting)**: No additional tokens (data structure conversion)
- **Stage 4 (Inference)**: **Maximum token consumption** (~num × tokens_per_sample)
  - If `num=16` and average response is 500 tokens: 16 × (prompt_tokens + 500 completion_tokens)
- **Stage 5 (Extraction)**: No model tokens (regex/parsing only)
- **Stage 6 (Voting)**: No model tokens (ensemble aggregation only)

Total token budget ≈ `num_questions × num_samples × average_tokens_per_sample × 2` (prompt + completion)

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
