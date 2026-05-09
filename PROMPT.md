# Prompt Template

This template is a self-contained, dataset-agnostic prompt designed to achieve optimal performance using Chain-of-Thought (CoT) reasoning with majority voting across model samples. This method proved effective in various reasoning tasks, including mathematical, scientific, and multiple-choice problems. The template requires minimal external dependencies and integrates:

1. The Chain-of-Thought (CoT) framework with concise and clear scaffolding.
2. Light instructions to name key principles relevant to the problem.
3. An auto-detect rule for answer formats, ensuring adaptability across diverse datasets.

## The Prompt

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

### Explanation of Placeholder Variables
- `{exemplars}`: Optional. Include worked examples formatted as `Question: ...\nAnswer: ...`, ending each answer with `\boxed{...}`. Few-shot exemplars work best for challenging datasets; leave this blank otherwise.
- `{question}`: The specific question to solve.

## Instructions for Use

1. **Setup the Prompt:** Substitute `{question}` with your question and optionally add 1–5 examples to `{exemplars}`.
2. **Sampling Responses:** Generate N model responses with a non-zero temperature (e.g., ~0.7). N = 16 is a recommended starting value.
3. **Extract Answers:** Isolate the final `\boxed{answer}` from each response.
4. **Majority Vote:** Identify the mode (frequent answer) among the responses. Return the mode as the final output.

## Advantages Over Complex Strategies

- Simplicity: Avoids unnecessary complex orchestration strategies such as multi-agent debate or tree-branching.
- Cost-Effective: Maintains precision without extra token usage for branching or intermediate simulations.
- Proven Effectiveness: Outperforms heavier strategies in controlled evaluations when paired with majority voting.

The given prompt framework ensures a universal, efficient foundation for reasoning tasks while leveraging the robustness of Chain-of-Thought reasoning boosted by majority sampling.