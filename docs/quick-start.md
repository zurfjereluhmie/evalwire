# Quick Start

This guide walks you through uploading a testset to Arize Phoenix and running your first experiment with evalwire.

## Prerequisites

- Python >= 3.10
- A running Arize Phoenix instance (see [Phoenix docs](https://docs.arize.com/phoenix) for local setup via Docker)
- Your Phoenix endpoint exported as `PHOENIX_BASE_URL` (default: `http://localhost:6006`)

## Install

```bash
pip install 'evalwire[langgraph]'
```

## Step 1 — Prepare your CSV testset

Create a CSV file with at minimum a `tags` column, an input column, and an expected-output column:

```csv
user_query,expected_output,tags
"What is a large language model?","A deep learning model trained on text.","rag_pipeline"
"How does retrieval augmented generation work?","RAG retrieves context before generating.","rag_pipeline"
```

- `tags` — names the Phoenix dataset the row belongs to. Pipe-delimit to assign a row to multiple datasets: `es_search|source_router`.

## Step 2 — Upload to Phoenix

```bash
evalwire upload --csv data/testset.csv
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--on-exist skip` | `skip` | Leave existing datasets untouched |
| `--on-exist overwrite` | | Delete and re-create |
| `--on-exist append` | | Add rows to existing dataset |
| `--input-keys COL` | `user_query` | Comma-separated input column names |
| `--output-keys COL` | `expected_output` | Comma-separated output column names |

## Step 3 — Write a task

Create `experiments/rag_pipeline/task.py`:

```python
from evalwire.langgraph import invoke_node
from agent.graph import RAGState, retrieve

async def task(example) -> list[str]:
    result = await invoke_node(retrieve, example.input["user_query"], RAGState)
    return result["retrieved_titles"]
```

## Step 4 — Choose an evaluator

You can write a custom evaluator function or use one of the built-in factories.

### Using a built-in evaluator

Create `experiments/rag_pipeline/top_k.py`:

```python
from evalwire.evaluators import make_top_k_evaluator

top_k = make_top_k_evaluator(K=5)
```

All nine built-in factories are available from `evalwire.evaluators`:

| Factory | Returns | When to use |
|---|---|---|
| `make_top_k_evaluator(K)` | `float` | Ranked retrieval — score by position |
| `make_membership_evaluator()` | `bool` | Classification / routing label |
| `make_exact_match_evaluator()` | `bool` | Single correct string answer |
| `make_contains_evaluator()` | `bool` | Output must include a required phrase |
| `make_regex_evaluator()` | `bool` | Output must match a regex pattern |
| `make_json_match_evaluator(keys)` | `float` | Structured output key-value matching |
| `make_schema_evaluator(schema)` | `bool` | JSON Schema conformance |
| `make_numeric_tolerance_evaluator(atol, rtol)` | `bool` | Numeric answer within tolerance |
| `make_llm_judge_evaluator(model, prompt, schema)` | `float\|bool` | LLM-as-a-judge |

### Writing a custom evaluator

```python
def top_k(output: list[str], expected: dict) -> float:
    """Fraction of expected titles present in the top-K retrieved results."""
    expected_titles = {t.strip() for t in expected.get("expected_output", "").split("|") if t.strip()}
    if not expected_titles:
        return 0.0
    hits = sum(1 for t in output if t in expected_titles)
    return hits / len(expected_titles)
```

### Using the LLM judge

```python
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from evalwire.evaluators import make_llm_judge_evaluator

class Verdict(BaseModel):
    explanation: str
    score: bool  # True = correct

llm_judge = make_llm_judge_evaluator(
    model=init_chat_model("gpt-4o-mini"),
    prompt_template=(
        "Output: {output}\n"
        "Expected: {expected_output}\n"
        "Is the output correct? Think step by step, then set score."
    ),
    output_schema=Verdict,
)
```

Requires `pip install 'evalwire[llm-judge]'`.

## Step 5 — Run experiments

```bash
evalwire run --experiments experiments/
```

Results appear in the Phoenix UI under the **Experiments** tab for each dataset.

## Using a config file

Avoid repeating flags by creating `evalwire.toml`:

```toml
[dataset]
csv_path = "data/testset.csv"
on_exist = "skip"

[experiments]
dir = "experiments"
prefix = "eval"
concurrency = 4
```

Then simply run:

```bash
evalwire upload
evalwire run
```
