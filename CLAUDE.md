# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Research code for the ACL 2025 paper *"Rethinking the Role of Prompting Strategies in LLM Test-Time Scaling: A Perspective of Probability Theory"*. The framework runs an LLM × dataset × prompting-strategy grid, samples many responses per question, and analyzes how each strategy scales under majority voting.

The paper's headline empirical finding: as sampling time and compute scale, **simple CoT / DiP overtake complex strategies** (ToT, Self-Refine, Multi-Agent Debate) that had higher pass@1. Keep this in mind when adding or changing strategies — complexity is not assumed to help.

## Environment

```bash
conda create -n rethinking_prompting python=3.11
conda activate rethinking_prompting
pip install -r requirements.txt
```

Python 3.11 is required (the pinned `vllm==0.8.4` and the rest of the stack target it). `atomic-agents` is pinned at `1.1.11` because the v2.x line requires Python 3.12+ — see `SKILL.md` for the v1↔v2 translation table when porting docs-style examples.

Before running anything you must edit two hard-coded paths/secrets:

- `main.py` → `hf_token = "hf_YourTokenHere"` (used by `huggingface_hub.login`)
- `dataset.py` → `base_path = "xxx/xxx/.../rethinking_prompting"` (used to derive `log_path = base_path/logs`; all run logs are written there)

API-based providers also need `--google_api_key`, `--openai_api_key`, and `--openai_base_url` passed on the command line.

## How to run experiments

All experiments are launched through `main.py`. The repo provides example shell scripts in `scripts/` that string together one `python main.py ...` invocation per strategy:

```bash
bash scripts/Qwen_GSM8K.sh      # vLLM + Qwen2.5-7B on GSM8K, all 8 strategies
bash scripts/GPT_GSM8K.sh       # OpenAI-API path
bash scripts/Gemini_GSM8K.sh    # Gemini path
bash scripts/Qwen_MATH.sh       # vLLM + Qwen on MATH
```

Single command shape:

```bash
python main.py \
    --model_name Qwen/Qwen2.5-7B-Instruct \
    --model_type vllm \                  # vllm | openai | gemini
    --dataset GSM8K \                    # see DATASET_CONFIGS in main.py
    --reasoning DiP \                    # DiP CoT L2M SBP AnP S-RF ToT MAD
    --shot 0 \
    --batchsize 10 \
    --range_begin 0 --range_end 32 \     # produces 32 samples per question
    --gpu 0,1
```

`--range_begin`/`--range_end` define the sample index span — the "N" in majority@N. Logs are written one file per index `n` under `<base_path>/logs/...`, so reruns resume from where prior logs leave off (`read_logs` in `dataset.py`).

## Strategy-specific argument constraints

Hard constraints enforced by `assert`s in `main.py` (around L322-L335):

| `--reasoning` | Required `--shot` | Notes |
| --- | --- | --- |
| `DiP`, `SBP`    | forced to `0`           | `SBP` uses 1-shot on MMLU automatically |
| `CoT`           | `0`, `1`, or `5`        | only on `GSM8K`/`GSM-Hard`/`MATH`; `0` elsewhere |
| `L2M`           | any                     | few-shot count |
| `AnP`           | `1`, `3`, or `5`        | shot = number of analogous problems to generate |
| `S-RF`          | forced to `0`           | `range_end - range_begin` must equal 1 |
| `ToT`           | `3`, `5`, or `10`       | shot = number of CoT reasoning paths; **requires CoT logs to already exist** for those shot counts (see `handle_tot_reasoning`) |
| `MAD`           | forced to `0`           | `batchsize`, `max_num_workers` forced to 1; range span must be 1; **requires DiP logs for sample indices 0, 1, 2** (see `setup_mad_reasoning`) |

Implication: when reproducing a row from a scripts/ file, run the strategies **in script order** — `DiP` and `CoT` produce the logs that `MAD` and `ToT` depend on.

## Evaluation

After `main.py` populates `<base_path>/logs/`, score with:

```bash
python eval_csv_N.py    --model_name <model> --dataset <dataset>   # accuracy vs. N samples
python eval_csv_cost.py --model_name <model> --dataset <dataset>   # accuracy vs. token cost
```

Both scripts iterate over the strategies in the logs directory and write an `.xlsx` plus the matplotlib figures used in the paper. Adjust `sampling_times` inside the eval scripts to change which points are plotted.

## Architecture: the big picture

The system is six files plus two data-only directories. Understand the flow before editing any one of them — most "fix one strategy" tasks actually touch three.

```
                        ┌─ prompts/<DATASET>.py        (dataset-specific prompt templates
                        │                               + answer-format strings)
                        ▼
main.py ───────► dataset.read_dataset() ───► dataset.create_prompt(args)
   │                                                  │
   │   args.reasoning ∈                               │ builds args.query / args.messages
   │   {DiP, CoT, L2M, SBP, AnP,                      │ from the per-dataset Prompts class
   │    S-RF, ToT, MAD}                               ▼
   │                                          model.LLM_generate(args)
   │   strategy branches in                           │
   │   get_model_outputs(args) compose                ├─ vLLM local inference
   │   single- or multi-pass calls to ─────────────► ├─ openai.OpenAI (gpt_parallel_generate)
   │   LLM_generate                                   └─ Gemini (model.Gemini)
   │
   ▼
dataset.record_logs(...)  →  <base_path>/logs/<model>/<dataset>/<strategy>/<shot>/<n>.json
                                              │
                                              ▼
                              eval_csv_N.py / eval_csv_cost.py
                                  (majority vote over indices in range)
```

### `main.py` — orchestration

- Argparse defines model, dataset, strategy, shot count, sampling range, hardware, and API keys. `MODEL_CONFIGS`, `DATASET_CONFIGS`, and `PROMPT_FORMATS` (each dataset's `Prompts.prompt_format`) are wired in at the top of `__main__`.
- `get_model_outputs(args)` is the strategy dispatcher. Each branch builds prompts and orchestrates the calls to `LLM_generate` in a different shape:
  - `DiP / CoT / AnP / L2M` — single prompt, single call.
  - `SBP` (Step-Back Prompting) — two-call pipeline, exactly as `main.py:98-124`. Call 1 samples `args.num = N` "key principles" per question. The code then temporarily sets `args.num = 1`, iterates over each `(question i, principle sample j)` pair, stashes `args.principles = principles[i][j]["output"]` on `args`, and appends `create_prompt(args, i)[0]` to `args.query` — yielding `L × N` solver prompts in total. Call 2 produces one solution per prompt; results are re-paired as `records[i][j] = {"principles": principles[i][j], "solution": solutions[N*i + j][0]}`, and `args.num` is restored to `N` at the end. `del args.principles` cleans up the per-pair scratch field before the second call.
  - `S-RF` — N+1 calls per question: initial DiP solution, then `args.rounds` × (feedback → refined answer) using `refine1_feeback_prompt` / `refine1_refine_prompt`.
  - `ToT` — generates `--shot` independent CoT reasoning paths *upstream* (in `handle_tot_reasoning`), then asks the model to choose among them. ToT therefore **reads prior CoT logs from disk**.
  - `MAD` — three "agents" debate over `args.rounds`. Each round calls `dataset.construct_message` to merge the other two agents' previous answers into the next user turn. **Bootstraps from three prior DiP logs** (`setup_mad_reasoning`).
- The two large mutually-similar loops at the bottom (lines ~376-505) differ only by `args.model_type`: the vLLM path iterates `range(begin_num, len(dataset_list), batchsize)`; the API path computes missing sample indices and batches those. Per-dataset key normalization (e.g. `example["question"] = example.pop("Problem")` for AIME) happens *inside* each loop — keep them in sync if you add a dataset.

### `dataset.py` — prompts, I/O, answer parsing

- `read_dataset(args)` loads via `datasets.load_dataset` (HuggingFace); GPQA additionally goes through `load_GPQA_examples` for choice shuffling with `args.seed`.
- `create_prompt(args, index=None)` is the single funnel that maps `(args.reasoning, args.dataset)` → either `args.query` (list of strings) or per-sample multi-turn messages. It pulls dataset-specific templates from `prompts/`.
- `record_logs` / `read_logs` define the on-disk log layout under `<base_path>/logs/...` and are how strategies resume and how downstream strategies (ToT, MAD) consume prior runs.
- `parse_answer(args, input_str)` (L622+) and the boxed/`\\boxed{...}` helpers (`last_boxed_only`, `remove_boxed`, `is_equiv`, `_strip_string`, `_fix_fracs`, etc.) implement the answer-extraction and equivalence logic borrowed from the MATH benchmark. `examine_output` is the per-record scoring entry point. **Any new dataset must plumb both a prompt class in `prompts/<NAME>.py` and an `examine_output`/`parse_answer` branch here.**
- Cost accounting (`get_cost`) hard-codes per-million-token prices for Gemini / GPT — update both `dataset.get_cost` and the duplicate `get_cost` in `eval_csv_N.py` / `eval_csv_cost.py` when adding a model.

### `model.py` — backend abstraction

- `load_model(args)` dispatches on `args.model_type` and stashes the client/LLM on `args` so subsequent `LLM_generate` calls can reuse it.
- `LLM_generate(args)` returns a nested list shaped `[num_questions][num_samples] = {"output": str, "input_tokens": int, "output_tokens": int}`. Strategies and the eval scripts both assume this shape.
- Three backends:
  - **vLLM** — local batched generation; uses `--gpu`, `--dtype`, `--max_new_tokens`, `--temperature`, `--top_p`.
  - **OpenAI** (`gpt_parallel_generate` + `ThreadPoolExecutor` with `--max_num_workers`) — also handles any OpenAI-compatible base URL via `--openai_base_url`.
  - **Gemini** (`class Gemini`) — disables all safety filters (`BLOCK_NONE`) because reasoning prompts otherwise trigger spurious refusals.

### `prompts/<DATASET>.py`

Each file exports a module-level `prompt_format` string (the answer-format clause, e.g. `"\\boxed{answer}"` for GSM8K, multiple-choice instructions for MMLU/GPQA) and per-strategy template functions consumed by `dataset.create_prompt`. Adding a strategy means adding a function to each dataset prompt file *and* a branch in `dataset.create_prompt`.

### `PROMPT.md` and `SKILL.md`

- `PROMPT.md` documents the dataset-agnostic CoT + majority-voting prompt template the paper recommends as a baseline. Use it as the reference shape when adding a strategy.
- `SKILL.md` is the Claude Code skill that teaches the **atomic-agents** framework (v2 docs, v1.1.11 translation table) and the canonical CoT-agent skeleton for this repo. Read it before wrapping any new strategy as a typed agent.

## Working in this codebase

- The CLI exposes `args` as a single mutable namespace that flows through every module. Most "global state" lives on `args` (`args.query`, `args.messages`, `args.records_tot`, `args.previous_record`, etc.). Treat `args` as the implicit context object — mutating it inside a strategy branch is normal here.
- `main.py` has two near-duplicate loops (vLLM vs API). When you change per-dataset key normalization or per-batch setup, change **both**.
- `hf_token` and `base_path` are placeholder strings on disk — running without editing them will fail at `huggingface_hub.login` or at the first `os.path.join(log_path, ...)`.
- Reasoning-strategy assertions in `main.py` are strict — most arg-validation bugs surface there rather than deeper in the stack.
