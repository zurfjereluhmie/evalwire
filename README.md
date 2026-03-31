# evalwire

> Systematic, reproducible evaluation of LangGraph nodes and subgraphs against human-curated testsets, tracked in Arize Phoenix.

---

[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![CI](https://github.com/zurfjereluhmie/evalwire/actions/workflows/ci.yml/badge.svg)](https://github.com/zurfjereluhmie/evalwire/actions/workflows/ci.yml)
![PyPI - Version](https://img.shields.io/pypi/v/evalwire?cacheSeconds=0)

## What it does

When iterating on a LangGraph agent, it is hard to know whether a change to a specific node improved or degraded its behaviour. Running the full graph end-to-end is expensive and makes it difficult to attribute a score change to a specific component.

`evalwire` solves this by:

- Turning a human-curated CSV of queries and expected outputs into versioned [Arize Phoenix](https://phoenix.arize.com/) datasets.
- Letting you define a **task** that isolates and invokes individual LangGraph nodes independently of the rest of the graph.
- Running those tasks against the stored datasets, scoring each output with one or more **evaluators**, and recording results in Phoenix — giving you a reproducible, comparable experiment per run.

---

## Installation

```bash
pip install evalwire
# With LangGraph node-isolation helpers:
pip install 'evalwire[langgraph]'
# With LLM-as-a-judge evaluator:
pip install 'evalwire[llm-judge]'
# Everything:
pip install 'evalwire[all]'
```

---

## Quick start

### 1. Upload your testset

```bash
evalwire upload --csv data/testset.csv
```

The CSV must contain a `tags` column whose values name the target Phoenix dataset (multiple tags can be pipe-delimited: `es_search|source_router`).

### 2. Structure your experiments

```
experiments/
├── es_search/
│   ├── task.py        # defines: async def task(example) -> Any
│   └── top_k.py       # defines: def top_k(output, expected) -> float
└── source_router/
    ├── task.py
    └── accuracy.py
```

### 3. Run experiments

```bash
evalwire run --experiments experiments/
```

---

## Built-in evaluators

All factories are importable from `evalwire.evaluators` and return a callable with
signature `(output, expected: dict) -> float | bool`.

| Factory | Returns | Use case |
|---|---|---|
| `make_top_k_evaluator(K=20)` | `float` | Position-weighted retrieval scoring |
| `make_membership_evaluator()` | `bool` | Classification / routing label check |
| `make_exact_match_evaluator()` | `bool` | Extractive QA, single ground-truth string |
| `make_contains_evaluator()` | `bool` | Free-text generation, required phrase present |
| `make_regex_evaluator()` | `bool` | Structured format validation (dates, IDs, …) |
| `make_json_match_evaluator(keys)` | `float` | Tool-call / structured-output key matching |
| `make_schema_evaluator(schema)` | `bool` | JSON Schema conformance |
| `make_numeric_tolerance_evaluator(atol, rtol)` | `bool` | Math / calculation tasks with tolerance |
| `make_llm_judge_evaluator(model, prompt, schema)` | `float\|bool` | LLM-as-a-judge with structured output |

### Example

```python
from evalwire.evaluators import make_top_k_evaluator, make_exact_match_evaluator

# Drop the factory return value into your experiment directory as the evaluator
top_k = make_top_k_evaluator(K=5)
exact = make_exact_match_evaluator()
```

### LLM judge

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

---

## Node isolation

Use `invoke_node` to call a single LangGraph node without compiling a full graph:

```python
from evalwire.langgraph import invoke_node

async def task(example) -> list[str]:
    result = await invoke_node(retrieve, example.input["user_query"], RAGState)
    return result["retrieved_titles"]
```

---

## CLI reference

| Command                          | Description                              |
| -------------------------------- | ---------------------------------------- |
| `evalwire upload --csv PATH`     | Upload CSV testset to Phoenix            |
| `evalwire run --experiments DIR` | Discover and run all experiments         |
| `evalwire run --name NAME`       | Run a single named experiment            |
| `evalwire run --dry-run N`       | Run N examples without recording results |
| `evalwire run --concurrency N`   | Run N experiments in parallel            |

---

## Configuration

Create `evalwire.toml` in your project root to avoid repeating flags:

```toml
[dataset]
csv_path = "data/testset.csv"
on_exist = "skip"

[experiments]
dir = "experiments"
prefix = "eval"
concurrency = 4
```

---

## Requirements

- Python >= 3.10
- `arize-phoenix >= 13.0, < 14`
- A running Phoenix instance (local or cloud)
