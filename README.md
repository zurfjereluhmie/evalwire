# evalwire

> Systematic, reproducible evaluation of LangGraph nodes and subgraphs against human-curated testsets, tracked in Arize Phoenix.

---

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

| Command | Description |
|---------|-------------|
| `evalwire upload --csv PATH` | Upload CSV testset to Phoenix |
| `evalwire run --experiments DIR` | Discover and run all experiments |
| `evalwire run --name NAME` | Run a single named experiment |
| `evalwire run --dry-run N` | Run N examples without recording results |
| `evalwire run --concurrency N` | Run N experiments in parallel |

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
