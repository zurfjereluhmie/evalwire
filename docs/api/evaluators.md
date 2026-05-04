# evalwire.evaluators

Built-in evaluator factories. Each factory returns a callable with the standard evalwire evaluator signature:

```python
def evaluator(output, expected: dict) -> float | bool: ...
```

The `expected` dict always contains at minimum an `"expected_output"` key whose value is parsed by the shared `_parse_expected` helper (handles plain strings, Python-literal strings such as `"['a','b']"`, and pipe-delimited strings).

All factories are importable directly from `evalwire.evaluators`:

```python
from evalwire.evaluators import (
    make_top_k_evaluator,
    make_membership_evaluator,
    make_exact_match_evaluator,
    make_contains_evaluator,
    make_regex_evaluator,
    make_json_match_evaluator,
    make_schema_evaluator,
    make_numeric_tolerance_evaluator,
    make_llm_judge_evaluator,
)
```

For a guide on writing your own evaluators, see [Writing Custom Evaluators](../guides/custom-evaluators.md).

---

## Retrieval

::: evalwire.evaluators.top_k.make_top_k_evaluator

---

## Classification

::: evalwire.evaluators.membership.make_membership_evaluator

---

## String matching

::: evalwire.evaluators.exact_match.make_exact_match_evaluator

::: evalwire.evaluators.contains.make_contains_evaluator

::: evalwire.evaluators.regex.make_regex_evaluator

---

## Structured output

::: evalwire.evaluators.json_match.make_json_match_evaluator

::: evalwire.evaluators.schema.make_schema_evaluator

---

## Numeric

::: evalwire.evaluators.numeric_tolerance.make_numeric_tolerance_evaluator

---

## LLM judge

::: evalwire.evaluators.llm_judge.make_llm_judge_evaluator
