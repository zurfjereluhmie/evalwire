# Concepts

This page explains the mental model behind evalwire before you dive into the quick start or API reference.

## The four building blocks

### Datasets

A **dataset** is a named collection of test examples stored in Arize Phoenix. Each example has input fields (e.g. `user_query`) and expected-output fields (e.g. `expected_output`). evalwire creates datasets by uploading a CSV testset and splitting it by a tag column.

One CSV row can belong to multiple datasets. Just pipe-delimit the tag value:

```
user_query,expected_output,tags
"find cycling paths","url-a | url-b","es_search | source_router"
```

This row appears in both the `es_search` and `source_router` datasets.

### Experiments

An **experiment** is the result of running a task against a dataset and scoring each output with one or more evaluators. Phoenix records every experiment run with a timestamp so you can compare results across code changes.

evalwire discovers experiments by scanning a directory. Each subdirectory that contains a `task.py` is treated as one experiment. The directory name must match a Phoenix dataset name:

```
experiments/
  es_search/         ← matched to the "es_search" Phoenix dataset
    task.py
    top_k.py         ← evaluator
  source_router/     ← matched to the "source_router" Phoenix dataset
    task.py
    is_in.py         ← evaluator
```

### Tasks

A **task** is an `async` function that receives a Phoenix example object and returns the output to be scored. Its job is to call your system under test and return a result in whatever form your evaluators expect.

```python
# experiments/es_search/task.py
async def task(example):
    user_query = example.input["user_query"]
    return await my_retrieval_function(user_query)
```

The function must be named `task`.

### Evaluators

An **evaluator** is a plain callable with the signature:

```python
def evaluator(output, expected: dict) -> float | bool: ...
```

Each evaluator file in an experiment directory is auto-loaded. The callable must share its name with the file:

```python
# experiments/es_search/top_k.py
from evalwire.evaluators import make_top_k_evaluator

top_k = make_top_k_evaluator(K=5)
```

Return `float` (0.0–1.0) for graded scoring or `bool` for pass/fail. Phoenix displays both.

## The experiment lifecycle

```
CSV testset
    │
    │  evalwire upload
    ▼
Phoenix Datasets  (one per unique tag)
    │
    │  evalwire run
    ▼
Task function  (called once per example)
    │
    ▼
Output
    │
    │  evaluator(output, expected)
    ▼
Experiment Results  (stored in Phoenix, visible in UI)
```

1. **Upload**: `evalwire upload` reads your CSV, groups rows by the tag column, and creates or updates one Phoenix dataset per unique tag value.
2. **Run**: `evalwire run` scans the experiments directory, matches each subdirectory to a Phoenix dataset by name, calls `task` on every example, and scores the output with each evaluator file found in that directory.
3. **Compare**: open the Phoenix UI, navigate to the dataset, and switch to the **Experiments** tab to compare runs side-by-side.

## How `expected` is structured

Inside every evaluator, the `expected` parameter is a dict containing all output columns from the original CSV row. The most important key is `"expected_output"`, which evalwire parses with `_parse_expected`:

- Plain string `"answer"` → `["answer"]`
- Pipe-delimited string `"a | b"` → `["a", "b"]`
- Python-literal string `"['a', 'b']"` → `["a", "b"]`
- Already a list → returned as-is

Most built-in evaluators read `expected["expected_output"]` for you. When writing a custom evaluator you can also access any other column directly: `expected["my_column"]`.
