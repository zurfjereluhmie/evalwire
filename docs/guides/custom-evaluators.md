# Writing Custom Evaluators

evalwire evaluators are plain Python callables. This guide covers the full contract, common patterns, and best practices.

## The evaluator contract

Every evaluator must follow this signature:

```python
def evaluator_name(output, expected: dict) -> float | bool: ...
```

- `output` is whatever your `task` function returned for a given example.
- `expected` is a dict of all output columns from the original CSV row. The key `"expected_output"` is always present.
- Return `float` (0.0 to 1.0) for graded scoring or `bool` for pass/fail.

## The `expected` dict

`expected` contains every output column from the CSV row. For a CSV like:

```csv
user_query,expected_output,tags
"find cycling paths","url-a | url-b","es_search"
```

`expected` will be:

```python
{"expected_output": ["url-a", "url-b"]}
```

evalwire parses `expected_output` through `_parse_expected` before passing it to evaluators:

| CSV value | Parsed result |
|---|---|
| `"answer"` | `["answer"]` |
| `"a \| b"` | `["a", "b"]` |
| `"['a', 'b']"` | `["a", "b"]` |
| already a list | unchanged |

You can also add extra columns to the CSV and read them directly from `expected`:

```python
def my_evaluator(output, expected: dict) -> bool:
    threshold = float(expected.get("score_threshold", 0.5))
    return float(output) >= threshold
```

## When to return `float` vs `bool`

Use `float` when the quality of the output is graded (e.g. how many correct items were retrieved). Use `bool` when the output is simply correct or incorrect.

Phoenix displays both types. Float scores are averaged across examples; bool scores are shown as a pass rate.

## File and name conventions

Each evaluator lives in its own file inside the experiment directory. The callable must share the name of the file (without `.py`):

```
experiments/
  es_search/
    task.py
    top_k.py       <- must define a callable named `top_k`
    exact_match.py <- must define a callable named `exact_match`
```

Multiple evaluators per experiment are supported: just add more files.

## Using a built-in factory

The simplest approach is to assign the factory's return value at module level:

```python
# experiments/es_search/top_k.py
from evalwire.evaluators import make_top_k_evaluator

top_k = make_top_k_evaluator(K=5)
```

All nine factories are importable from `evalwire.evaluators`. See the [Evaluators API reference](../api/evaluators.md) for full signatures.

## Writing a custom function

For use cases not covered by the built-ins, write a plain function:

```python
# experiments/es_search/recall.py

def recall(output: list[str], expected: dict) -> float:
    expected_items = set(expected.get("expected_output", []))
    if not expected_items:
        return 0.0
    hits = sum(1 for item in output if item in expected_items)
    return hits / len(expected_items)
```

## Composing multiple evaluators

Run several evaluators on the same experiment by adding one file per evaluator:

```
experiments/
  es_search/
    task.py
    recall.py
    precision.py
    exact_match.py
```

All three will appear as separate score columns in the Phoenix experiment view.

## Error handling

If your evaluator raises an exception for a single example, the experiment run fails for that example. Guard against bad output types to keep a run from aborting mid-way:

```python
def recall(output, expected: dict) -> float:
    if not isinstance(output, list):
        return 0.0
    expected_items = set(expected.get("expected_output", []))
    if not expected_items:
        return 0.0
    return sum(1 for item in output if item in expected_items) / len(expected_items)
```

For the LLM judge specifically, the `on_error` parameter controls behaviour when the model call fails:

```python
llm_judge = make_llm_judge_evaluator(
    model=model,
    prompt_template=PROMPT,
    output_schema=Verdict,
    on_error="silent",   # returns 0.0 / False on failure instead of raising
)
```
