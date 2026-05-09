# Unified Prompt — Rethinking Prompting (ACL 2025)

This document is the single self-contained natural-language specification of the entire `rethinking_prompting` pipeline. It consolidates every Python module in the repo (`main.py`, `dataset.py`, `model.py`, `eval_csv_N.py`, `eval_csv_cost.py`, and the per-dataset templates under `prompts/`) into one prompt that an LLM (or a developer) can read end-to-end to (a) reproduce the experiments, (b) generate any of the eight prompting strategies for any of the six benchmarks, and (c) evaluate scaling under both budgets used in the paper.

The paper's empirical claim is that, under majority voting at scale, simple Chain-of-Thought (CoT) and Direct Prompting (DiP) eventually overtake more elaborate strategies (ToT, MAD, S-RF, SBP, AnP, L2M) even when the elaborate strategy has a higher pass@1. This prompt is therefore organized so the simple strategies are the default and the elaborate ones are opt-in.

---

## 1. High-level recipe (the recommended default)

```text
Please answer the given question. Your final answer should appear at the very end of your response in the form \boxed{answer}.

Choose the contents of \boxed{...} to match the question's answer type:
  - a single numerical value for arithmetic/word problems (e.g., \boxed{72})
  - a closed-form mathematical expression for symbolic problems (e.g., \boxed{\dfrac{7}{20}})
  - a single capital letter for multiple-choice questions (e.g., \boxed{C})
  - the shortest unambiguous string for any other short-answer question

Before writing the final answer, do the following, briefly:
  1. Identify the key concepts, definitions, or principles the question is testing. State them in one or two lines.
  2. Solve the problem step by step, showing intermediate computations or deductions. Let's think step by step.
  3. Double-check the result against the question and the chosen answer format, then emit the \boxed{...} on its own at the end.

{exemplars}

Question: {question}
Answer:
```

- `{exemplars}` — optional 0–5 worked examples formatted as `Question: …\nAnswer: … \boxed{…}`. Empty by default; use few-shot only on the harder math sets (GSM8K/MATH 1- or 5-shot helps; MMLU/GPQA 0-shot is best in this codebase).
- `{question}` — the problem statement (and, for multiple choice, the choices block from §3).

Sample N completions (default N = 16) at temperature 0.7, top-p 0.9, max_new_tokens = 4096; extract the final `\boxed{…}` from each; majority-vote (ties broken by random pick). This is the protocol the paper uses for "Majority@N".

---

## 2. The eight prompting strategies

Every strategy below ultimately reduces to either: (a) one model call per sample, or (b) a small fixed orchestration with multiple calls per sample. After producing the per-sample answer, the **same** majority-voting step from §1 is applied across N independent runs.

### 2.1 DiP — Direct Prompting (`shot=0`)

Just ask. Shot is fixed at 0.

```text
{question}{prompt_format}
```

Where `{prompt_format}` is the dataset-specific tail from §3 (e.g. `" Your final answer should be a single numerical number, in the form \boxed{answer}, at the end of your response."`).

### 2.2 CoT — Chain-of-Thought (`shot ∈ {0,1,5}` for GSM8K/GSM-Hard/MATH; `shot=0` elsewhere)

```text
Please answer the given question.{prompt_format}

{few_shot_exemplars_if_any}

Question: {question} Let's think step by step.
Answer:
```

For MMLU / GPQA, append `Let's think step by step:` directly to the choices block instead of `Let's think step by step.\nAnswer:`.

### 2.3 L2M — Least-to-Most (`shot=1` for GSM8K/GSM-Hard, `shot=0` elsewhere)

Decompose the question into progressive sub-questions, solve each, then assemble the final answer.

For GSM8K/GSM-Hard, prepend the canonical 1-shot:
```text
Question: Elsa has 5 apples. Anna has 2 more apples than Elsa. How many apples do they have together?
Answer: Let's break down this problem: 1. How many apples does Anna have? 2. How many apples do they have together?
1. Anna has 2 more apples than Elsa. So Anna has 2 + 5 = 7 apples.
2. Elsa and Anna have 5 + 7 = 12 apples together.
The answer is: \boxed{12}.
```

For MATH/AIME/MMLU/GPQA, use the 0-shot variant: `"… break down the question into progressive sub-questions. Answer the sub-questions and get the final result …"` followed by the dataset's answer-format requirement.

### 2.4 SBP — Step-Back Prompting (`shot=0`; MMLU uses 1-shot for physics/chemistry)

Two model calls per sample:

1. **Extract principles** — "You are an expert at {subject}. Your task is to extract the {subject} concepts and principles involved in solving the problem." → emits a `Principles involved:` block. For MMLU physics and chemistry, a one-shot worked example of the principles block is included (Coulomb's law for physics, precipitation/molar-mass/limiting-reactant for chemistry).
2. **Answer using principles** — "You are an expert at {subject}. You are given a {subject} problem and a set of principles involved in solving the problem. Solve the problem step by step by following the principles." with `{principles}` substituted from step 1.

`{subject}` is `mathematics` for GSM8K/GSM-Hard/MATH/AIME, `physics`/`chemistry`/`biology` for MMLU subsets, and the GPQA `High-level domain` field for GPQA.

### 2.5 AnP — Analogous Prompting (`shot ∈ {1,3,5}`)

Single model call. Ask the model to first recall N analogous (but distinct) problems with their solutions, then solve the target problem. The instruction varies only in the count — "Recall an example…", "Recall three examples…", or "Recall five examples…". Each recalled example must end its answer with `\boxed{…}` (math) or `"The correct answer is (X)"` (multiple choice). For MMLU/GPQA the instruction is parametrized by `{subject}`.

### 2.6 S-RF — Self-Refine (`shot=0`, range size = 1, default `rounds=5`)

Iterative single-agent refinement. Per question:

1. Initial answer: run DiP → `output0`.
2. For round `j = 1..rounds`:
   - **Feedback turn**: append user message `"Review your previous answer and find problems with your answer."` → model emits `problems{j}`.
   - **Refine turn**: append user message `"Based on the problems you found, improve your answer." + {prompt_format}` → model emits `output{j}`.

The conversation is preserved across rounds. The final scored answer is the parsed `output{j}` for the chosen round j. Token accounting sums prompt+completion tokens of `output0` plus every `problems{k}` and `output{k}` for k = 1..j.

### 2.7 ToT — Tree of Thoughts (`shot ∈ {3,5,10}`)

Two stages, where stage 1 reuses CoT outputs:

1. **Generate `shot` candidate solutions** by running CoT (`shot=0`) `shot` times — each call is logged as `CoT_0_{n}.json` for n = 0..shot-1. These are read back from disk.
2. **Select the best** — concatenate the question with `Solution 1: …`, …, `Solution {shot}: …`, then ask:
   ```text
   Given the question and several solutions, decide which solution is the most promising. Analyze each solution in detail, then conclude in the last line "The index of the best solution is x", where x is the index number of the solution.
   ```
   Parse the chosen index with regex `index of the best solution is (\d+)` (fallback regex `\*\*(\d+)\*\*`); clamp to `[1, shot]`; on parse failure pick uniformly at random from `[0, shot)`.

Majority voting in ToT happens over the **selected indices** across N runs of step 2; the final answer is the parsed answer of the most-selected candidate solution.

### 2.8 MAD — Multi-Agent Debate (`shot=0`, batchsize=1, max_workers=1, default `rounds=5`, 3 agents)

Three agents, each seeded with an independent DiP context (the three are read from `DiP_0_0.json`, `DiP_0_1.json`, `DiP_0_2.json`). For round = 1..rounds, for each agent i:
- If round > 1, prepend the other two agents' previous-round answers as:
  ```text
  These are the answers to the question from other agents:

   One agent answer: ```{agent_j_response}```

   One agent answer: ```{agent_k_response}```

   Using the solutions from other agents as additional information, can you provide your answer to the {math|}problem?
   The original {math|}problem is {question}. {dataset_specific_format_tail}
  ```
  where the format tail is the dataset's `prompt_format` (math / MATH / MMLU / GPQA variants in §3).
- The agent generates a fresh response which becomes that round's record.

Majority voting at round j is across the 3 agents' parsed answers in `round{j}`. (Only GSM8K, GSM-Hard, MATH, AIME, GPQA, MMLU-* are wired up; other datasets raise.)

---

## 3. The six benchmarks (datasets + answer formats)

Each row is "dataset → loader → key field → answer-format tail appended after the question (`prompt_format`)".

| Dataset | HF / source | Key field for grading | Answer format tail |
|---|---|---|---|
| **GSM8K** | `openai/gsm8k` `main`, split `test` | `answer.split("#### ")[-1]` (numeric) | `" Your final answer should be a single numerical number, in the form \boxed{answer}, at the end of your response."` |
| **GSM-Hard** | `reasoning-machines/gsm-hard` train | `target` (numeric) | Same as GSM8K but prefixed with: `"  The given information may not conform to common sense and the result may be a nonsense decimal or negative number, it's okay, output it instead of considering it is unreasonable."` |
| **MATH** | `HuggingFaceH4/MATH-500` test | `answer` (LaTeX) | `" Your final result should be in the form \boxed{answer}, at the end of your response."` |
| **AIME_2024** | modelscope `AI-ModelScope/AIME_2024` train (set `HF_DATASETS_OFFLINE=1`) | `Answer` (integer string) | Same as MATH |
| **GPQA** | `Idavidrein/gpqa` `gpqa_main` train, with shuffled choices | letter A–D (computed at load: index of `Correct Answer` in shuffled `[Incorrect 1, Incorrect 2, Incorrect 3, Correct]`, mapped to A–D) | `Please choose the correct choice. Your last sentence should be "The correct answer is (insert answer here, which is only the letter of the choice)".` |
| **MMLU-{high_school_physics, high_school_chemistry, high_school_biology}** | `cais/mmlu` `<subject>`, split `test` | `["A","B","C","D","E"][answer]` | Same as GPQA |

Multiple-choice questions are wrapped as:

```text
Question:
{question}

Choices:
(A) {choice1}
(B) {choice2}
(C) {choice3}
(D) {choice4}

```

GPQA choices are shuffled at load time using `args.seed`, then re-keyed so the new index of the correct answer becomes the gold letter. MMLU subjects must literally be one of the three subsets used by the paper.

---

## 4. Answer parsing & equivalence

Per dataset, after generation:

- **GSM8K / GSM-Hard** — find the *last* `\boxed{…}` and strip non-numeric chars; multi-stage fallbacks: `boxed{(.*)}`, `\{([0-9 \-.,$]*)\}`, `\*\*(.*)\*\*`, then any numeric run. Cast to `float`. Grade as correct iff `|float(key) − pred| < 1e-4`.
- **MATH / AIME_2024** — last `\boxed{…}` only; strip via the canonical `_strip_string` normalizer:
  - drop `\n`, `\!`, `\$`, `\%`; collapse `\\\\` → `\\`; replace `tfrac`/`dfrac` → `frac`; drop `\left`/`\right`; drop `^{\circ}`/`^\circ`; remove right-side `\text{ …}` units; rewrite leading `.` → `0.`; drop `j → i`; if the string is `k = …`/`q = …` strip the LHS; fix `\sqrt3` → `\sqrt{3}`; drop spaces; fix `\frac1b` → `\frac{1}{b}` and bare `a/b` → `\frac{a}{b}`; map `0.5` → `\frac{1}{2}`. Compare normalized strings with `==`.
- **GPQA / MMLU-*** — letter regex cascade against the model output:
  1. `correct answer is \*\*(.)\*\*` — first char of group; if not in `[A,B,C,D]`, try `\((.)\)` inside the match.
  2. `correct answer is (.?)` similarly.
  3. `\((.)\)` anywhere; first hit whose char is a valid letter.
  4. `\{(.)\}` anywhere; same.
- **ToT selection** — `index of the best solution is (\d+)`, fallback `\*\*(\d+)\*\*`, else `None` → random.

The default for "no parseable answer" in the majority-voting step is to drop `None` candidates; if everything is `None`, keep a single `None` and count it as wrong.

---

## 5. Sampling, parallelism, and the run loop

Hyperparameter defaults (CLI):

- `--temperature 0.7 --top_p 0.8` (note: vLLM path internally uses `top_p=0.9` regardless), `--max_new_tokens 4096`.
- `--range_begin 0 --range_end 16` → samples `n = 0..15` (so N up to 16 by default; 32 in some scripts).
- `--batchsize 10` (forced to `1` when `reasoning == MAD`).
- `--max_num_workers 1` (used only by API backends; forced to `1` for MAD).
- `--rounds 5` (used by S-RF and MAD).
- `--seed 0`.
- `--model_type ∈ {vllm, gemini, openai}`; `--gpu "4,5"` controls `CUDA_VISIBLE_DEVICES` and `tensor_parallel_size`.
- `--dtype bfloat16` for vLLM.

Per (dataset, model, reasoning, shot) the driver iterates over the dataset in `batchsize` chunks, builds prompts via the §2 templates, calls `LLM_generate` `args.num` times in a single batched chat call (vLLM) or `args.num` parallel completions (OpenAI `n=`, Gemini `candidate_count=`), parses each response, and appends each completion to the per-`n` log file. Logs live at:

```text
{base_path}/logs/{dataset}/{model_name_short}/{reasoning}_{shot}_{n}.json
```

Existing logs are read back to support resumption (the loop skips already-processed indices). `model_name_short` is the basename after the last `/` of the HF id.

Backends:

- **vLLM** — `LLM(model=..., trust_remote_code=True, tensor_parallel_size=len(gpu.split(",")), dtype=...)`; one `chat(messages, SamplingParams(temperature, n=num, max_tokens, top_p=0.9))` call per batch.
- **OpenAI-compatible** — `OpenAI(api_key, base_url).chat.completions.create(model, messages, n=num, logprobs=True, max_tokens=max_new_tokens)`. `completion_tokens` is `len(choice.logprobs.content)` (per-choice token count).
- **Gemini** — `google.generativeai.GenerativeModel(model).generate_content(messages, GenerationConfig(candidate_count=num), safety_settings=BLOCK_NONE for all four harm categories)`. Retries up to `N=3` on exception with 10 s sleep; only candidates with `finish_reason == 1` are kept.

Role mapping for non-Gemini: `roles = ['user', 'assistant']`, alternating starting from user; an optional system message is prepended. For Gemini: `roles = ['user', 'model']`, `parts=[…]`, no system role.

---

## 6. Evaluation (`eval_csv_N.py` and `eval_csv_cost.py`)

Both scripts read the per-strategy JSON logs and compute Majority@N accuracy. They differ only in the x-axis they report and the per-strategy cap on N.

Strategies enumerated and their shot resolution at eval time:
- `DiP` → `shot=0`
- `CoT` → `shot=0`
- `L2M` → `shot=1` for GSM8K/GSM-Hard, else `shot=0`
- `ToT_3` / `ToT_5` / `ToT_10` → `reasoning=ToT`, `shot ∈ {3,5,10}`, N=1
- `S-RF` → `shot=0`, N derived from `(len(record) - 1) // 2`
- `SBP` → `shot=0`
- `AnP` → `shot=1`
- `MAD` → `shot=0`, N = `len(record["round1"])` (= 3)

For each method-N pair, the script:
1. Loads up to N log files (one per `n`).
2. For each question, parses the answer from each log according to the strategy (DiP/CoT/L2M/AnP read `record.output`; SBP reads `record.solution.output`; S-RF reads `record["output{m+1}"].output`; ToT reads the chosen solution's `output`; MAD reads the round-m+1 list).
3. Optionally shuffles the per-`n` order (`--shuffle True`) and repeats 5 times to average over which subset of N runs is taken.
4. Majority-votes parsed answers, grades with the dataset rule from §4, averages accuracy across the 5 random shuffles, and writes one row to `{dataset}_N.xlsx` (or `{dataset}_cost.xlsx`) per (method, shot, N).

Token accounting (used for the cost x-axis): per question, per the strategy:
- DiP/CoT/L2M/AnP: prompt_tokens of the first run + sum of completion_tokens across runs.
- SBP: principles' prompt_tokens (once) + completion_tokens for each principles run + every solution run's prompt and completion tokens.
- S-RF: output0's tokens + (problems_k.prompt + output_k.prompt + problems_k.completion + output_k.completion) for k = 1..N.
- ToT: each candidate solution's tokens + each `choose` call's tokens.
- MAD: sum across rounds of all 3 agents' prompt and completion tokens.

Cost-per-million-tokens used to convert tokens → dollars:

```
gemini-1.5-flash:        prompt 0.075   + completion 0.30
gpt-3.5-turbo-0613:      prompt 1.50    + completion 2.00
gpt-4o-mini:             prompt 0.15    + completion 0.60
others (default):        prompt 0.15    + completion 0.60
```
divided by 10⁶.

Per-strategy maximum N values (the two scripts disagree here on purpose):

| Strategy | `eval_csv_N` (uniform) | `eval_csv_cost` |
|---|---|---|
| DiP / CoT / L2M / SBP / AnP | 16 | 100 / 90 / 75 / 25 / 40 |
| S-RF / MAD | 16 | 10 / 10 |
| ToT | 1 (per shot ∈ {3,5,10}) | same |

`eval_csv_N` plots accuracy vs `sampling_times = [1, 3, 5, 7, 10, 15]`; `eval_csv_cost` plots accuracy vs total tokens at `sampling_times = [1, 3, 5, 7, 10, 12, 15]`. Both produce a scatter+line per strategy, color-mapped from violet (DiP) → red (MAD), with markers `^` for non-iterative and `o` for iterative strategies, and a top "best-at-N" indicator row marked `P*_N` / `P*_cost`. Output files: `logs/{dataset}/{model}/pics/Performance_N.png` and `Performance_cost.png` (600 DPI).

---

## 7. End-to-end usage

To run inference for one (model, dataset, strategy):

```bash
python main.py \
  --model_name Qwen/Qwen2.5-7B-Instruct \
  --model_type vllm \
  --dataset GSM8K \
  --reasoning DiP --shot 0 \
  --range_begin 0 --range_end 16 \
  --batchsize 10 --gpu 0,1
```

Available `--reasoning` values and their valid `--shot`:
- `DiP`: 0
- `CoT`: 0, 1, 5 (the latter two only on GSM8K/GSM-Hard/MATH)
- `L2M`: 0 (or 1 on GSM8K/GSM-Hard)
- `SBP`: 0
- `AnP`: 1, 3, 5
- `S-RF`: 0 (`range_end - range_begin == 1`)
- `ToT`: 3, 5, 10
- `MAD`: 0 (`range_end - range_begin == 1`)

Available `--dataset`: `GSM8K, GSM-Hard, MATH, AIME_2024, GPQA, MMLU-high_school_physics, MMLU-high_school_chemistry, MMLU-high_school_biology`.

Available `--model_name`: any HF id (vLLM), any OpenAI-compatible model (with `--openai_api_key`/`--openai_base_url`), or Gemini model (with `--google_api_key`).

After running enough samples, evaluate:

```bash
python eval_csv_N.py    --model_name Qwen/Qwen2.5-7B-Instruct --dataset GSM8K
python eval_csv_cost.py --model_name Qwen/Qwen2.5-7B-Instruct --dataset GSM8K
```

Setup that must happen before any run: set `hf_token` in `main.py`, set `base_path` in `dataset.py` to the repo root (so `logs/` resolves), and provide whichever API keys the chosen `--model_type` requires.

---

## 8. Why the recommended default in §1 works

The paper's theoretical result is that under majority voting:
- Easy questions (per-sample correctness probability > 0.5 over the answer distribution) converge to 100% as N grows.
- Hard questions converge to 0%.
- Strategies that concentrate probability mass on a single mode — even if that mode is wrong some of the time — beat strategies that spread mass across many modes.

DiP and CoT empirically concentrate mass best on most benchmarks; ToT/MAD/S-RF/SBP/AnP/L2M can have higher pass@1 by exploring more, but the extra modes drag down their large-N accuracy. The single prompt in §1 is therefore the recommended default, and §§2–6 exist to reproduce the comparison rather than to be deployed in production.

For deployment with majority voting at scale: use §1 with N = 16 at temperature ≈ 0.7, parse the last `\boxed{…}` per §4, and majority-vote.
