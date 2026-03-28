# evalwire — Package Specification

> Systematic, reproducible evaluation of LangGraph nodes and subgraphs against
> human-curated testsets, tracked in Arize Phoenix.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Concepts](#2-core-concepts)
3. [Two-Phase Model](#3-two-phase-model)
4. [CSV Schema & Configuration](#4-csv-schema--configuration)
5. [Experiment Discovery Convention](#5-experiment-discovery-convention)
6. [Node Isolation Helpers](#6-node-isolation-helpers)
7. [Built-in Evaluators](#7-built-in-evaluators)
8. [DatasetUploader](#8-datasetuploader)
9. [ExperimentRunner](#9-experimentrunner)
10. [Observability Setup](#10-observability-setup)
11. [CLI](#11-cli)
12. [Configuration File](#12-configuration-file-evalwiretoml)
13. [Dependencies & Python Version](#13-dependencies--python-version)
14. [Phoenix 13.x API Surface](#14-phoenix-13x-api-surface)
15. [Non-Goals](#15-non-goals)
16. [Migration Guide](#16-migration-guide)

---

## 1. Overview

### Problem

When iterating on an AI agent graph (e.g. a LangGraph pipeline), it is hard to
know whether a change to a specific node has improved or degraded its behaviour.
Running the entire graph end-to-end is expensive, slow, and makes it difficult
to attribute a score change to a specific component.

### Solution

`evalwire` provides a thin layer on top of Arize Phoenix experiments that:

- Turns a human-curated CSV of queries and expected outputs into versioned
  Phoenix datasets (one dataset per logical group of test cases).
- Lets you define a **task** that isolates and invokes one or several LangGraph
  nodes independently of the rest of the graph.
- Runs those tasks against the stored datasets, scores each output with one or
  more **evaluators**, and records results in the Phoenix UI — giving you a
  reproducible, comparable experiment per run.

### Positioning

`evalwire` is **not** a testing framework and does not generate synthetic data.
It is a lightweight orchestration layer that enforces a consistent project
structure so that the same evaluation workflow can be repeated across any
LangGraph-based agent project.

---

## 2. Core Concepts

| Concept        | Description                                                                                                                                                                       |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dataset**    | A named collection of `(input, expected_output)` pairs stored in Arize Phoenix. Corresponds to one logical aspect of the agent (e.g. `es_search`, `source_router`).               |
| **Task**       | An `async` callable `(Example) -> Any` that runs the node(s) under test for one example and returns a JSON-serialisable output.                                                   |
| **Evaluator**  | A callable `(output, expected) -> float \| bool` that scores the task output against the expected output for one example.                                                         |
| **Experiment** | A single (dataset × task × evaluators) execution recorded in Phoenix. Each run of `evalwire run` produces a new, time-stamped experiment that can be compared with previous ones. |

---

## 3. Two-Phase Model

```
Phase 1 — Upload                Phase 2 — Run
─────────────────               ────────────────────────────────────────
data/testset.csv                experiments/
       │                               ├── es_search/
       ▼                               │   ├── task.py
DatasetUploader.upload()               │   └── top_k.py
       │                               └── source_router/
       ▼                                   ├── task.py
Arize Phoenix Datasets                     └── is_in.py
  ├── "es_search"                                │
  └── "source_router"                            ▼
                                    ExperimentRunner.run()
                                           │
                                           ▼
                                    Arize Phoenix Experiments
                                      (per-example scores + traces)
```

Phase 1 is typically run once when the testset changes. Phase 2 is run every
time a node implementation changes and you want to measure the impact.

---

## 4. CSV Schema & Configuration

### Default Schema

| Column            | Type                   | Description                                    |
| ----------------- | ---------------------- | ---------------------------------------------- |
| `user_query`      | `str`                  | Natural-language input to the agent            |
| `expected_output` | `str` (pipe-delimited) | One or more expected values, separated by `\|` |
| `tags`            | `str` (pipe-delimited) | Dataset membership tags, separated by `\|`     |

A row can belong to multiple datasets simultaneously by listing multiple tags:

```
user_query,expected_output,tags
"find cycling paths","url-a | url-b","es_search | source_router"
```

### Custom Column Names

All column names and the delimiter character are configurable (see
[DatasetUploader](#8-datasetuploader) and
[Configuration File](#12-configuration-file-evalwiretoml)).

### Pipe-Splitting Behaviour

During upload, every column whose values contain the configured delimiter is
automatically split into a Python `list`. This includes `tags` and
`expected_output` by default. Any other column that uses the same delimiter is
also split — this is intentional and allows multi-value fields beyond
`expected_output`.

### `on_exist` Behaviour

| Value         | Behaviour                                                                                |
| ------------- | ---------------------------------------------------------------------------------------- |
| `"skip"`      | If a dataset with the same name already exists in Phoenix, leave it untouched (default). |
| `"overwrite"` | Delete the existing dataset and re-create it with the new data.                          |
| `"append"`    | Add new examples to the existing dataset without removing existing ones.                 |

---

## 5. Experiment Discovery Convention

Each experiment lives in its own subdirectory under a configurable
`experiments/` root:

```
experiments/
└── <dataset_name>/
    ├── __init__.py          # optional; auto-generated by evalwire if absent
    ├── task.py              # required — defines the task callable
    └── <evaluator_name>.py  # one or more evaluator files
```

### Rules

- The **directory name** must match the name of a Phoenix dataset (e.g.
  `es_search` must correspond to a dataset named `"es_search"`).
- `task.py` must export a module-level async callable named `task` with the
  signature:
  ```python
  async def task(example: phoenix.experiments.types.Example) -> Any: ...
  ```
- Each evaluator file (any `.py` file in the directory that is not `task.py` or
  `__init__.py`) must export a module-level callable whose name matches the
  filename (without `.py`):
  ```python
  # top_k.py
  def top_k(output: Any, expected: dict) -> float: ...
  ```
- A directory that has no `task.py` is silently skipped.
- Multiple evaluator files per experiment are allowed.

### Auto-Discovery

`ExperimentRunner` scans the `experiments/` directory at startup, imports each
valid experiment module, and wires up `(task, [evaluators])` automatically. No
explicit registration is required.

---

## 6. Node Isolation Helpers

These utilities live in `evalwire.langgraph` (available when the
`evalwire[langgraph]` extra is installed).

### 6.1 `build_subgraph`

Assembles a minimal linear `StateGraph` from a list of extracted node
callables. Useful when you want to test a small chain of nodes (e.g.
`es_generate_query → es_search`) without running the full graph.

```python
from evalwire.langgraph import build_subgraph

graph = build_subgraph(
    nodes=[
        ("es_generate_query", my_graph.es_connector.generate_query),
        ("es_search",         my_graph.es_connector.search),
    ],
    state_cls=State,
    input_cls=InputState,
    name="es_search_eval",          # optional, used for Phoenix tracing
    checkpointer=None,              # optional
)

output = await graph.ainvoke(InputState(messages=[HumanMessage(content=query)]))
```

**Signature:**

```python
def build_subgraph(
    nodes: list[tuple[str, Callable]],
    state_cls: type,
    input_cls: type | None = None,
    *,
    name: str | None = None,
    checkpointer: Any = None,
) -> CompiledStateGraph:
    ...
```

- `nodes` is an ordered list of `(node_name, node_callable)` pairs. Edges are
  added in declaration order: `START → nodes[0] → nodes[1] → … → END`.
- `state_cls` is the LangGraph state dataclass for the graph.
- `input_cls` is the optional input-schema dataclass (passed as
  `input_schema=input_cls` to `StateGraph`).

### 6.2 `invoke_node`

Directly calls a single LangGraph node method as a standalone async function,
bypassing graph compilation entirely. Suitable for pure routing or
classification nodes that have no side effects on other nodes.

```python
from evalwire.langgraph import invoke_node

result = await invoke_node(
    node_fn=my_graph._source_router,
    query="find cycling paths near Lyon",
    state_cls=State,
)
```

**Signature:**

```python
async def invoke_node(
    node_fn: Callable,
    query: str,
    state_cls: type,
    *,
    message_field: str = "messages",
    config: RunnableConfig | None = None,
) -> Any:
    ...
```

- Constructs a `state_cls` instance with a single `HumanMessage` placed in
  `message_field`.
- Calls `await node_fn(state=state, config=config or RunnableConfig())`.
- Returns the raw return value of the node.

---

## 7. Built-in Evaluators

These live in `evalwire.evaluators` and are **factory functions** that return a
configured evaluator callable.

### 7.1 `make_top_k_evaluator`

Position-weighted retrieval scoring. Designed for ranked list outputs (e.g.
Elasticsearch results) where the position of a correct item matters.

```python
from evalwire.evaluators import make_top_k_evaluator

top_k = make_top_k_evaluator(K=20)
# top_k(output, expected) -> float
```

**Algorithm:**

```
score_per_item = 1.0 - (position / K)  if item found in output[:K]  else  0.0
final_score    = mean(score_per_item for item in expected_output)
```

- `output` — `list[str]`, ordered by relevance (most relevant first).
- `expected["expected_output"]` — `list[str] | str`; a `str` is parsed with
  `ast.literal_eval`.
- Returns a `float` in `[0.0, 1.0]`.
- An item found at position 0 (rank 1) scores `1.0`. An item not found in the
  top `K` scores `0.0`. An item at position `K-1` scores `1/K`.

**Factory signature:**

```python
def make_top_k_evaluator(K: int = 20) -> Callable[[list[str], dict], float]:
    ...
```

### 7.2 `make_membership_evaluator`

Exact membership check. Designed for classification/routing outputs where the
expected value is one of a small set of labels.

```python
from evalwire.evaluators import make_membership_evaluator

is_in = make_membership_evaluator()
# is_in(output, expected) -> bool
```

- `output` — `str`, the predicted label.
- `expected["expected_output"]` — `list[str] | str`; a `str` is parsed with
  `ast.literal_eval`.
- Returns `True` if `output` is a member of the expected list, `False`
  otherwise. Phoenix converts `bool` to `1.0` / `0.0`.

**Factory signature:**

```python
def make_membership_evaluator() -> Callable[[str, dict], bool]:
    ...
```

---

## 8. DatasetUploader

```python
from evalwire import DatasetUploader
from phoenix.client import Client

uploader = DatasetUploader(
    csv_path="data/testset.csv",
    phoenix_client=Client(),
    input_keys=["user_query"],       # default
    output_keys=["expected_output"], # default
    tag_column="tags",               # default
    delimiter="|",                   # default
)

uploader.upload(on_exist="skip")
```

### Constructor

```python
class DatasetUploader:
    def __init__(
        self,
        csv_path: Path | str,
        phoenix_client: Client,
        input_keys: list[str] = ("user_query",),
        output_keys: list[str] = ("expected_output",),
        tag_column: str = "tags",
        delimiter: str = "|",
    ) -> None: ...
```

### `.upload()`

```python
def upload(
    self,
    on_exist: Literal["skip", "overwrite", "append"] = "skip",
) -> dict[str, Any]:
    """
    Upload one Phoenix dataset per unique tag value found in the CSV.

    Returns a dict mapping each tag name to the created/updated dataset object.
    """
    ...
```

**Internal steps:**

1. Load the CSV with `pandas.read_csv`.
2. Split any column whose values contain `delimiter` into Python lists (includes
   `tag_column` unconditionally).
3. Group rows by tag value — a row belonging to multiple tags appears in each
   group.
4. For each tag, call `client.datasets.create_dataset(dataframe, name, ...)`.
   Handle `on_exist` using public Phoenix 13.x APIs only:
   - `"skip"`: call `create_dataset` with `action="skip"` (or catch the
     conflict error and proceed).
   - `"overwrite"`: retrieve the dataset by name with
     `client.datasets.get_dataset(name=tag)`, delete it via
     `client.datasets.delete_dataset(id=...)`, then re-create.
   - `"append"`: retrieve the existing dataset and add examples with
     `client.datasets.add_examples(...)`.

---

## 9. ExperimentRunner

```python
from evalwire import ExperimentRunner
from phoenix.client import Client

runner = ExperimentRunner(
    experiments_dir="experiments",
    phoenix_client=Client(),
    concurrency=1,
    dry_run=False,
)

runner.run()                            # run all discovered experiments
runner.run(names=["es_search"])         # run a specific subset
```

### Constructor

```python
class ExperimentRunner:
    def __init__(
        self,
        experiments_dir: Path | str,
        phoenix_client: Client,
        *,
        concurrency: int = 1,
        dry_run: bool | int = False,
    ) -> None: ...
```

- `concurrency` — number of experiments to run in parallel (default: 1,
  sequential).
- `dry_run` — if `True`, run one example per experiment without uploading
  results to Phoenix. If an `int`, run that many examples. Passed directly to
  `client.experiments.run_experiment(dry_run=...)`.

### `.run()`

```python
def run(
    self,
    names: list[str] | None = None,
    *,
    experiment_name_prefix: str = "eval",
    metadata: dict | None = None,
) -> list[Any]:
    """
    Discover, load, and run experiments.

    Parameters
    ----------
    names
        If provided, only run experiments whose directory names are in this
        list. If None, run all discovered experiments.
    experiment_name_prefix
        Prefix for the auto-generated experiment name in Phoenix.
        Default name format: "{prefix}_{dataset_name}_{iso_timestamp}".
    metadata
        Extra key/value pairs attached to each experiment record in Phoenix.

    Returns
    -------
    list
        One experiment result object per experiment, as returned by
        client.experiments.run_experiment().
    """
    ...
```

### Discovery Logic

For each subdirectory `<name>/` under `experiments_dir`:

1. Check that `task.py` exists — skip if absent.
2. Import `<name>.task` and retrieve the `task` attribute.
3. Collect all other `.py` files (excluding `__init__.py`), import them, and
   retrieve the callable whose name matches the filename stem.
4. Retrieve the Phoenix dataset whose name equals `<name>` via
   `client.datasets.get_dataset(name=name)`. If no dataset exists, log a
   warning and skip.
5. Call `client.experiments.run_experiment(dataset, task, evaluators, ...)`.

---

## 10. Observability Setup

```python
from evalwire import setup_observability
from openinference.instrumentation.langchain import LangChainInstrumentor

tracer_provider = setup_observability(
    instrumentors=[LangChainInstrumentor()],
)
```

**Signature:**

```python
def setup_observability(
    instrumentors: list[Any] | None = None,
    *,
    auto_instrument: bool = True,
) -> TracerProvider:
    """
    Register Phoenix as the OpenTelemetry tracer provider and instrument
    the provided frameworks.

    Parameters
    ----------
    instrumentors
        List of OpenInference instrumentor instances to activate.
        Each must implement .instrument(tracer_provider=...).
    auto_instrument
        Passed to phoenix.otel.register(). When True, Phoenix will attempt
        to auto-detect and instrument known libraries.

    Returns
    -------
    TracerProvider
        The registered tracer provider, for use with additional manual
        instrumentation if needed.
    """
    ...
```

### Optional Extras

| Extra                 | Installs                                           |
| --------------------- | -------------------------------------------------- |
| `evalwire[langchain]` | `openinference-instrumentation-langchain`          |
| `evalwire[openai]`    | `openinference-instrumentation-openai`             |
| `evalwire[langgraph]` | `langgraph` (enables `evalwire.langgraph` helpers) |
| `evalwire[all]`       | All of the above                                   |

---

## 11. CLI

The `evalwire` command is installed as a console script entry point.

### `evalwire upload`

Upload a CSV testset to Arize Phoenix as one or more named datasets.

```
evalwire upload [OPTIONS]

Options:
  --csv PATH              Path to the CSV file. Overrides config.
  --on-exist [skip|overwrite|append]
                          How to handle existing datasets. Default: skip.
  --input-keys TEXT       Comma-separated input column names. Default: user_query.
  --output-keys TEXT      Comma-separated output column names. Default: expected_output.
  --tag-column TEXT       Column used for dataset splitting. Default: tags.
  --delimiter TEXT        Pipe-split delimiter. Default: |.
  --config PATH           Path to evalwire.toml. Default: ./evalwire.toml.
  --help                  Show this message and exit.
```

### `evalwire run`

Discover and execute all registered experiments against their Phoenix datasets.

```
evalwire run [OPTIONS]

Options:
  --experiments PATH      Path to the experiments directory. Default: ./experiments.
  --name TEXT             Run only the named experiment(s). Repeatable.
  --dry-run [INTEGER]     Run without uploading results. Optional count of examples.
  --concurrency INTEGER   Number of parallel experiments. Default: 1.
  --prefix TEXT           Experiment name prefix in Phoenix. Default: eval.
  --config PATH           Path to evalwire.toml. Default: ./evalwire.toml.
  --help                  Show this message and exit.
```

### Exit Codes

| Code | Meaning                                                                   |
| ---- | ------------------------------------------------------------------------- |
| `0`  | All experiments completed (regardless of scores)                          |
| `1`  | One or more experiments failed to run (task error, missing dataset, etc.) |
| `2`  | Configuration or CLI argument error                                       |

---

## 12. Configuration File (`evalwire.toml`)

All CLI options can be set in `evalwire.toml` at the project root. CLI flags
take precedence over file values.

```toml
[dataset]
csv_path      = "data/testset.csv"
input_keys    = ["user_query"]
output_keys   = ["expected_output"]
tag_column    = "tags"
delimiter     = "|"
on_exist      = "skip"

[experiments]
dir           = "experiments"
concurrency   = 1
prefix        = "eval"

[phoenix]
# PHOENIX_BASE_URL and PHOENIX_API_KEY are read from environment variables.
# Set them here only if you need to override the environment.
# base_url    = "https://your-phoenix-instance.com"
# api_key     = "your-api-key"
```

### Environment Variables

Phoenix connection settings are read from the environment by the Phoenix client.
`evalwire` does not introduce additional environment variables.

| Variable           | Description                                              |
| ------------------ | -------------------------------------------------------- |
| `PHOENIX_BASE_URL` | URL of the Phoenix server (e.g. `http://localhost:6006`) |
| `PHOENIX_API_KEY`  | API key for Phoenix Cloud (not required for self-hosted) |

---

## 13. Dependencies & Python Version

### Runtime

| Package         | Version constraint          | Notes                                                 |
| --------------- | --------------------------- | ----------------------------------------------------- |
| Python          | `>=3.10`                    |                                                       |
| `arize-phoenix` | `>=13.0, <14`               | Required. Enforces public API surface.                |
| `pandas`        | `>=2.0`                     | CSV loading and manipulation.                         |
| `click`         | `>=8.0`                     | CLI interface.                                        |
| `tomli`         | `>=2.0` (Python <3.11 only) | TOML config parsing (stdlib `tomllib` used on 3.11+). |

### Optional Extras

| Extra                 | Package                                   | Version |
| --------------------- | ----------------------------------------- | ------- |
| `evalwire[langgraph]` | `langgraph`                               | `>=0.2` |
| `evalwire[langchain]` | `openinference-instrumentation-langchain` | `>=0.1` |
| `evalwire[openai]`    | `openinference-instrumentation-openai`    | `>=0.1` |
| `evalwire[all]`       | All of the above                          |         |

### `pyproject.toml` (skeleton)

```toml
[build-system]
requires      = ["hatchling"]
build-backend = "hatchling.build"

[project]
name            = "evalwire"
version         = "0.1.0"
description     = "Systematic evaluation of LangGraph nodes using Arize Phoenix experiments."
readme          = "README.md"
requires-python = ">=3.10"
dependencies = [
    "arize-phoenix>=13.0,<14",
    "pandas>=2.0",
    "click>=8.0",
    "tomli>=2.0; python_version < '3.11'",
]

[project.optional-dependencies]
langgraph = ["langgraph>=0.2"]
langchain = ["openinference-instrumentation-langchain>=0.1"]
openai    = ["openinference-instrumentation-openai>=0.1"]
all       = ["evalwire[langgraph,langchain,openai]"]

[project.scripts]
evalwire = "evalwire.cli:main"
```

---

## 14. Phoenix 13.x API Surface

`evalwire` targets `arize-phoenix >= 13.0` exclusively and uses only public SDK
APIs. No internal or private APIs are used.

### Dataset operations

```python
from phoenix.client import Client

client = Client()

# Create
dataset = client.datasets.create_dataset(
    dataframe=df,
    name="es_search",
    input_keys=["user_query"],
    output_keys=["expected_output"],
)

# Retrieve by name (public in 13.x)
dataset = client.datasets.get_dataset(name="es_search")

# Delete (public in 13.x, used for on_exist="overwrite")
client.datasets.delete_dataset(id=dataset.id)

# Append examples (public in 13.x, used for on_exist="append")
client.datasets.add_examples(dataset_id=dataset.id, examples=[...])
```

### Experiment execution

```python
from phoenix.client import Client

experiment = client.experiments.run_experiment(
    dataset=dataset,
    task=task,
    evaluators=[top_k, is_in],
    experiment_name="eval_es_search_2026-03-28T12:00:00",
    experiment_metadata={"dataset": "es_search", "run_by": "evalwire"},
    dry_run=False,
)
```

### Observability

```python
import phoenix
from phoenix.otel import register

tracer_provider = register(auto_instrument=True)
```

> **Note on prior versions:** The prototype implementation in
> `backend/evals_human_based/` targets `arize-phoenix >= 11.4, < 12` and works
> around two SDK gaps using private APIs: `_get_dataset_id_by_name` and
> `_client.delete("v1/datasets/{id}")`. These workarounds are **not present** in
> `evalwire`, which requires Phoenix 13.x where the equivalent public APIs are
> available.

---

## 15. Non-Goals

- **Not a testing framework.** `evalwire` produces scores, not pass/fail
  assertions. It does not integrate with `pytest` or any assertion library.
- **Not a synthetic data generator.** All testsets are human-curated. LLM-based
  testset generation is out of scope (see the sibling `evals/` module in the
  reference project for that use case).
- **Not coupled to any agent architecture.** `evalwire` imposes no constraints
  on the graph class, state schema, or node naming conventions beyond what is
  required by the task and evaluator calling conventions.
- **Not a Phoenix server manager.** `evalwire` assumes Phoenix is already
  running and reachable. It does not start, stop, or configure the Phoenix
  server.
- **Not a reranker or retrieval library.** The built-in evaluators measure
  retrieval quality; they do not perform retrieval themselves.

---

## 16. Migration Guide

This section describes how to migrate the existing implementation in
`backend/evals_human_based/` to `evalwire`.

### Phase 1 — Testset upload

**Before (`generate_testsets.py`):**

```python
from evals_human_based.generate_testsets import main
main(on_exist="skip")
```

**After (`evalwire`):**

```python
from evalwire import DatasetUploader
from phoenix.client import Client

DatasetUploader(
    csv_path="data/20260313_user-testing.csv",
    phoenix_client=Client(),
).upload(on_exist="skip")
```

Or via CLI:

```bash
evalwire upload --csv data/20260313_user-testing.csv --on-exist skip
```

### Phase 2 — Running experiments

**Before (`run_experiments.py`):**

```python
# Manual dispatch:
if name == "source_router":
    run_experiment(..., task=source_router_task, evaluators=[source_router_is_in])
elif name == "es_search":
    run_experiment(..., task=es_search_task, evaluators=[es_search_top_k])
```

**After (`evalwire`):**

```python
from evalwire import ExperimentRunner
from phoenix.client import Client

ExperimentRunner(
    experiments_dir="experiments",
    phoenix_client=Client(),
).run()
```

Or via CLI:

```bash
evalwire run
```

### Experiment files — no changes required

The existing `experiments/es_search/task.py` and
`experiments/source_router/task.py` files already conform to the `evalwire`
convention (module-level `task` async callable). The only required change is to
update the evaluator file exports:

| Current export                                    | Required export                                             |
| ------------------------------------------------- | ----------------------------------------------------------- |
| `from .top_k import top_k as es_search_top_k`     | `def top_k(output, expected)` at module level in `top_k.py` |
| `from .is_in import is_in as source_router_is_in` | `def is_in(output, expected)` at module level in `is_in.py` |

The prefixed aliases (`es_search_top_k`, `source_router_is_in`) in
`__init__.py` are only needed by the current manual dispatch in
`run_experiments.py` and can be removed once `evalwire` is adopted.

### Phoenix version upgrade

The existing code pins `arize-phoenix>=11.4.0,<12.0.0`. Upgrading to
`>=13.0,<14` will require:

1. Replacing `phoenix.experiments.run_experiment(...)` (module-level function)
   with `client.experiments.run_experiment(...)` (client method).
2. Removing the `_get_dataset_id_by_name` and `_client.delete(...)` calls in
   `generate_testsets.py` — use `client.datasets.get_dataset(name=...)` and
   `client.datasets.delete_dataset(id=...)` instead.
3. Verifying that `phoenix.otel.register(auto_instrument=True)` still has the
   same signature (it does as of 13.x).
