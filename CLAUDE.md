# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Reference implementation for the ACL 2025 Outstanding Paper "Rethinking the Role of Prompting Strategies in LLM Test-Time Scaling: A Perspective of Probability Theory" (Liu et al., 2025). The headline finding is that under majority-voting test-time scaling, simple CoT/DiP overtake more complex strategies (L2M, SBP, AnP, S-RF, ToT, MAD) as the number of samples grows, even when those complex strategies have a higher pass@1.

## Environment and install

- Python 3.11, conda env `rethinking_prompting`.
- `pip install -r requirements.txt` (pins `vllm==0.8.4`, `openai==1.53.0`, `google-generativeai==0.7.2`, `datasets==3.2.0`, `atomic-agents==1.1.11`).

Two placeholder strings on disk MUST be edited before running anything:

- `hf_token = "hf_YourTokenHere"` at `main.py:13` — used by `huggingface_hub.login`.
- `base_path = f"xxx/xxx/.../rethinking_prompting"` at `dataset.py:11` — `log_path` is derived from it, so logs cannot be written/read until this is a real path.

API-backed runs additionally need `--google_api_key` (Gemini) or `--openai_api_key` / `--openai_base_url` (OpenAI-compatible).

## Running experiments

Canonical invocation:

```
python main.py --model_name Qwen/Qwen2.5-7B-Instruct --model_type vllm \
    --dataset GSM8K --split test --reasoning DiP --shot 0 \
    --batchsize 10 --range_begin 0 --range_end 32 --gpu 0,1
```

Ready-made bash drivers live in `scripts/`: `Qwen_GSM8K.sh`, `Qwen_MATH.sh`, `GPT_GSM8K.sh`, `Gemini_GSM8K.sh`. Each script runs every strategy back-to-back in a specific order — that order matters (see next section).

`--model_type` is one of `vllm`, `gemini`, `openai`. Model choices are constrained to the `MODEL_CONFIGS` dict at `main.py:210`. `--range_begin`/`--range_end` defines how many independent samples per question are stored.

## Strategy constraints and dependencies

The valid `--shot`/`--range` values per strategy are enforced by asserts at `main.py:322-335`:

- `DiP`, `SBP` — `shot` is force-set to 0 (SBP uses 1-shot on MMLU internally via its prompt).
- `CoT` — on `GSM8K`/`GSM-Hard`/`MATH`, `shot` must be `0`, `1`, or `5`; on all other datasets `shot` must be `0`.
- `L2M` — no assert, but scripts use `--shot 1`.
- `AnP` — `shot` must be `1`, `3`, or `5` (number of analogous problems).
- `S-RF`, `MAD` — `shot` is force-set to 0 and `len(args.range) == 1` is required.
- `ToT` — `shot` must be `3`, `5`, or `10` (number of CoT reasoning paths).

Dependency chain (matters when reproducing a script):

- `ToT` (`handle_tot_reasoning`, `main.py:173`) reads prior `CoT` logs for every shot in `range(args.shot)`. Run `CoT` first.
- `MAD` (`setup_mad_reasoning`, `main.py:189`) reads prior `DiP` logs for sample indices `n=0`, `n=1`, `n=2`, and asserts all three exist and are equal-length. Run `DiP` with at least `--range_end 3` first.

Implication: when reproducing a `scripts/*.sh` file, run strategies in the script's order — the later ones consume earlier ones' JSON logs from `log_path`.

## Evaluation

```
python eval_csv_N.py    --model_name Qwen/Qwen2.5-7B-Instruct --dataset GSM8K
python eval_csv_cost.py --model_name Qwen/Qwen2.5-7B-Instruct --dataset GSM8K
```

`eval_csv_N.py` plots accuracy vs. number of samples N (majority voting). `eval_csv_cost.py` plots accuracy vs. token cost using the per-model rates in `get_cost` (`dataset.py:15`, mirrored in `eval_csv_N.py:35`).

## Architecture

- `main.py` — CLI, argument parsing, dataset preparation, and the strategy dispatcher `get_model_outputs` (`main.py:35`). Wraps each batch with the per-dataset field renaming (GSM8K `answer` -> `key`, MATH `problem` -> `question`, AIME `Problem` -> `question`, etc.).
- `dataset.py` — `read_dataset` (HuggingFace / ModelScope loaders), `create_prompt` (per-dataset, per-strategy prompt assembly, `dataset.py:159`), `record_logs`/`read_logs` (JSON log I/O under `log_path`), `parse_answer` plus MATH-style normalization helpers (`_strip_string`, `last_boxed_only_string`, `is_equiv`, `remove_boxed`), and `get_cost` for token pricing.
- `model.py` — `load_model` and `LLM_generate` with three backends: vLLM (local), OpenAI-compatible (`OpenAI` client), and Gemini (`google.generativeai`). The `Gemini` wrapper explicitly sets every `HarmCategory` to `BLOCK_NONE` (`model.py:53-58`) so safety filters do not silently drop math/science completions.
- `prompts/` — one module per dataset (`GSM8K.py`, `GPQA.py`, `GSM_Hard.py`, `MATH.py`, `MMLU.py`, `AIME.py`), each exporting a `prompt_format` plus per-strategy templates consumed by `create_prompt`.

## SBP (Step-Back Prompting) detail

SBP is a two-call pipeline implemented at `main.py:98-124`:

1. First `LLM_generate` call samples `args.num = N` "key principles" per question. With L questions this gives `principles` shaped `[L][N]`.
2. The code saves `num = args.num`, sets `args.num = 1`, then rebuilds `args.query` by iterating `for i in range(L): for j in range(num):`, attaching `args.principles = principles[i][j]["output"]` and appending `create_prompt(args, i)[0]`. This produces `L * N` solver prompts, one per (question, principle) pair.
3. `del args.principles` clears the per-pair scratch field before the next call.
4. Second `LLM_generate` returns `solutions` of length `L * N`, each with a single sample.
5. Records are reassembled as `records[i][j] = {"principles": principles[i][j], "solution": solutions[num * i + j][0]}`.
6. `args.num = num` is restored at the end so downstream logging sees the original sample count.

## See also

- See `SKILL.md` for the atomic-agents framework guide and a v1 <-> v2 translation table.
- See `PROMPT.md` for the dataset-agnostic CoT + majority-voting baseline prompt template the paper recommends.

## Working in this codebase

- `args` is the implicit mutable context object that flows through every module. `create_prompt`, `LLM_generate`, and the strategy branches in `get_model_outputs` all mutate fields like `args.query`, `args.messages`, `args.num`, `args.principles`, `args.records_tot`, `args.previous_record`, `args.continue_`. Save and restore any field you touch (the SBP block above is the canonical pattern).
- The bottom of `main.py` contains two near-duplicate loops: the vLLM branch (`main.py:376`) and the API branch (`main.py:440`). They share the same per-dataset field-renaming logic. Any new dataset has to be added to both `read_dataset`, `PROMPT_FORMATS` (`main.py:229`), the `letters`/`key` extraction in both loops, and the `prompts/` package — parallel edits required.
- `hf_token` (`main.py:13`) and `base_path` (`dataset.py:11`) are placeholder strings as checked in. Running anything without editing them fails immediately — `login` rejects the dummy token and `log_path` resolves to a non-existent directory under `xxx/xxx/.../`.
