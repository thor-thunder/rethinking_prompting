# Reproduce Prompt — A Single, Dataset-Agnostic Template

A self-contained prompt template that replicates this work's empirical
winner: **Chain-of-Thought (CoT) reasoning paired with majority voting over
multiple samples**. After benchmarking eight prompting strategies (direct,
chain-of-thought, least-to-most, step-back, analogical, tree-of-thoughts,
self-refine, multi-agent debate) across six reasoning datasets (grade-school
math, harder grade-school math, competition math, graduate-level science
Q&A, multi-task multiple choice, and AIME), the finding is that simple CoT
wins or ties the best at scale once self-consistency is applied — heavier
orchestrations spend extra tokens on intermediate planning that majority
voting eventually subsumes.

The template below fuses three elements into one prompt, with no external
dependencies:

- The CoT scaffold: a short instruction, a `\boxed{...}` answer convention,
  and the trigger phrase "Let's think step by step" before the answer slot.
- A lightweight "name the relevant principles first" cue (the strongest
  finding among the multi-step strategies), kept inline so it costs no extra
  round-trips.
- An auto-detect rule for the answer format so the same template works for
  numeric answers, mathematical expressions, multiple-choice letters, and
  short free-form answers without needing per-dataset variants.

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
target domain, paste them in front of the question in the same
`Question: ... \nAnswer: ...` format, ending each example's answer with its
own `\boxed{...}`. Few-shot exemplars are an accuracy-positive change for
hard datasets; leave the slot empty otherwise.

## How to use it

1. Substitute the question into `{question}` (and optionally drop one to
   five worked examples into `{exemplars}`). Send the resulting string to
   your LLM as a single user message.
2. Sample the model **N times** with a non-zero temperature — temperature
   around 0.7 and N up to 16 is a good operating point. Each sample is an
   independent rollout; do not condition later samples on earlier ones.
3. From each response, extract the contents of the *last* `\boxed{...}`
   that appears in the text. Strip whitespace and surrounding `$...$` if
   present. Treat that string as the candidate answer for that sample.
4. Take the **mode** of the N candidate answers (majority vote, ties broken
   arbitrarily). Output that as the final prediction. Sampling more, then
   voting, is what makes plain CoT competitive with — and usually better
   than — heavier prompting strategies.

## Why this template, and not one of the more elaborate strategies

Tree-of-thoughts, multi-agent debate, and analogical-prompting variants
spend extra tokens on intermediate orchestration: branching candidate
solutions, simulating critics, or generating analogous problems before the
real one. Once you sample plain CoT N times and take the majority vote,
those orchestrations no longer add accuracy worth their cost — the curves
flatten or cross. The template above keeps the proven CoT spine and adds
only the lightest principle-first cue, without any extra generation rounds.
