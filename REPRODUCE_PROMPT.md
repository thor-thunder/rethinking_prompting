# Reproduce Prompt — A Single, Dataset-Agnostic Template

A self-contained prompt template that replicates the empirical winner of this
repository's study: **Chain-of-Thought (CoT) reasoning paired with majority
voting over multiple samples**. The paper benchmarks 8 prompting strategies
(DiP, CoT, L2M, SBP, AnP, ToT, S-RF, MAD) across 6 datasets and finds that
once test-time compute is scaled via self-consistency, simple CoT — with the
exact phrasing pattern used in `prompts/GSM8K.py` and `prompts/MATH.py` — wins
or ties the best, while the orchestration-heavy strategies plateau.

This prompt fuses:

- The CoT scaffold from `prompts/GSM8K.py:9` (`cot_pre`) and `prompts/GSM8K.py:11`
  (`cot_0_shot`).
- The `\boxed{...}` answer convention used uniformly across every dataset
  module under `prompts/`.
- A lightweight "name the relevant principles first" cue borrowed from the
  Step-Back-Prompting templates at `prompts/GSM8K.py:126` (`SBP_extract`) and
  `prompts/GSM8K.py:133` (`SBP_answer`) — kept inline so it costs no extra
  round-trips.
- An auto-detect rule for the answer format so the same template works for
  numeric (GSM8K / GSM-Hard / AIME), mathematical-expression (MATH),
  multiple-choice (MMLU / GPQA), and free-form short-answer questions.

## The Prompt

```text
Please answer the given question. Your final answer should appear at the very
end of your response in the form \boxed{answer}.

Choose the contents of \boxed{...} to match the question's answer type:
  - a single numerical value for arithmetic / word problems (e.g. \boxed{72})
  - a closed-form mathematical expression for symbolic problems (e.g.
    \boxed{\dfrac{7}{20}})
  - a single capital letter for multiple-choice questions (e.g. \boxed{C})
  - the shortest unambiguous string for any other short-answer question

Before writing the final answer, do the following, briefly:
  1. Identify the key concepts, definitions, or principles the question is
     testing. State them in one or two lines.
  2. Solve the problem step by step, showing intermediate computations or
     deductions. Let's think step by step.
  3. Double-check the result against the question and the chosen answer
     format, then emit the \boxed{...} on its own at the end.

{exemplars}

Question: {question}
Answer:
```

`{exemplars}` is optional. If you have known-good worked examples for the
target dataset (e.g. the 5 worked GSM8K problems in `prompts/GSM8K.py:28` or
the 5 MATH problems in `prompts/MATH.py:28`), paste them in front of the
question in the same `Question: ... \nAnswer: ...` format; the few-shot
templates in this repo show this is a strict accuracy-positive change for
hard datasets. Leave it empty otherwise.

## How to use it (mirrors `main.py` + `eval_csv_N.py`)

1. Substitute the question into `{question}` (and optionally drop in
   `{exemplars}`). Send the resulting string to your LLM.
2. Sample the model **N times** with a non-zero temperature — the repo uses
   `temperature ≈ 0.7` and N up to 16 in `eval_csv_N.py`. Each sample is an
   independent rollout.
3. Parse each response with the `\boxed{...}` extractor (see
   `dataset.py:622` `parse_answer` and the `last_boxed_only_string` helper for
   reference logic).
4. Take the **mode** of the extracted answers — that is the majority-vote
   prediction. Per the paper's central result, this curve dominates the
   curves of ToT / MAD / AnP at the same N for CoT.

## Why this template, and not one of the more elaborate strategies

The repository's own `eval_csv_N.py` and `eval_csv_cost.py` curves show that
CoT and DiP are Pareto-optimal in (accuracy, samples) and (accuracy, dollars)
across all six benchmarks once N ≥ ~4. ToT, MAD and the analogical-prompting
variants spend extra tokens on intermediate orchestration that majority
voting eventually subsumes. The template above keeps the proven CoT spine
and adds only the lightest principle-first cue from SBP — which the paper
finds is the best of the multi-step strategies — without any extra
generation rounds.
