# evalwire.runner

`ExperimentRunner` auto-discovers experiment subdirectories, fetches the matching Phoenix dataset for each one, and runs the task against every example. Results are stored in Phoenix and returned as a list.

## Basic usage

```python
from phoenix.client import Client
from evalwire.runner import ExperimentRunner

client = Client()

runner = ExperimentRunner(
    experiments_dir="experiments",
    phoenix_client=client,
    concurrency=2,
)
results = runner.run()
```

## Directory layout

Each subdirectory of `experiments_dir` that contains a `task.py` is treated as one experiment. The directory name must exactly match a Phoenix dataset name:

```
experiments/
  es_search/           <- matches dataset named "es_search"
    task.py            <- must define async def task(example)
    top_k.py           <- evaluator: must define top_k = ...
    exact_match.py     <- evaluator: must define exact_match = ...
  source_router/       <- matches dataset named "source_router"
    task.py
    is_in.py
```

Subdirectories without `task.py` are silently skipped. Files (non-directories) at the top level of `experiments_dir` are also skipped.

## Experiment naming

Each run in Phoenix is named `{prefix}_{dataset_name}_{iso_timestamp}`. The default prefix is `"eval"`. Override it with `experiment_name_prefix`:

```python
results = runner.run(experiment_name_prefix="nightly")
# produces e.g. "nightly_es_search_2025-01-15T09:30:00"
```

## Running a subset

Pass `names` to run only specific experiments:

```python
results = runner.run(names=["es_search"])
```

## Dry run

Set `dry_run=True` (or `dry_run=N` to limit to N examples) to execute tasks without uploading results to Phoenix. Useful for smoke-testing your task code:

```python
runner = ExperimentRunner(
    experiments_dir="experiments",
    phoenix_client=client,
    dry_run=3,
)
runner.run()
```

## Async tasks

Tasks are `async` functions. evalwire wraps them in a per-thread event loop so Phoenix's synchronous runner can call them. The loop is kept open between calls (unlike `asyncio.run()`) so that async I/O libraries which reuse connections across calls work correctly.

## Error behaviour

If any experiment fails (dataset not found, task raises, evaluator raises), `runner.run()` raises `SystemExit(1)` after all experiments complete so that CI pipelines fail loudly. Successful experiments are still returned.

## Pitfalls

- The dataset name must match the directory name exactly (case-sensitive).
- At least one evaluator file is required per experiment. Phoenix raises an error if `run_experiment` is called with an empty evaluator list.
- Relative imports inside experiment modules work because evalwire adds the parent of `experiments_dir` to `sys.path` during discovery. It is removed again afterwards.

## See also

- [Concepts](../concepts.md) for the experiment lifecycle
- [Configuration Reference](../configuration.md) for `evalwire.toml` keys
- [CLI Reference](cli.md) for `evalwire run`

---

::: evalwire.runner
