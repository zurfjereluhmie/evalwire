# Troubleshooting

## "RuntimeError: Event loop is closed"

This happens when an async task is called multiple times and the event loop created by the first call was closed before the next call. evalwire uses a per-thread persistent event loop (since v0.2.2) to prevent this. If you see it:

- Make sure you are on evalwire `>=0.2.2`.
- Do not call `asyncio.run()` inside your task function. Use `await` directly.

## Phoenix connection errors

**Symptom:** `ConnectionRefusedError` or `httpx.ConnectError` when running `evalwire upload` or `evalwire run`.

**Causes and fixes:**

1. Phoenix is not running. Start it with `docker compose up -d` or follow the [Phoenix docs](https://docs.arize.com/phoenix).
2. The wrong endpoint is set. evalwire uses the `PHOENIX_COLLECTOR_ENDPOINT` environment variable. Check it points to your Phoenix instance:
   ```bash
   export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
   ```
3. A firewall or Docker network is blocking the port.

## "No CSV path provided"

```
Error: No CSV path provided. Use --csv or set csv_path in evalwire.toml.
```

Either pass `--csv data/testset.csv` on the command line or add this to `evalwire.toml`:

```toml
[dataset]
csv_path = "data/testset.csv"
```

## Dataset not found during `evalwire run`

```
SystemExit: 1
```

evalwire looks up each experiment directory name as a Phoenix dataset. If the dataset does not exist, the run fails. Make sure you have run `evalwire upload` first and that the directory name matches the dataset tag exactly (case-sensitive).

Run a subset to narrow down which experiment is failing:

```bash
evalwire run --name my_experiment
```

## Import errors for optional extras

**`ImportError: langgraph is required`**

Install the langgraph extra:

```bash
pip install 'evalwire[langgraph]'
```

**`ImportError: langchain-core is required to use make_llm_judge_evaluator`**

Install the llm-judge extra:

```bash
pip install 'evalwire[llm-judge]'
```

## CSV formatting issues

**Rows appear in the wrong dataset or not at all.**

- Check that the tag column name matches `tag_column` (default: `"tags"`). Use `--tag-column` or set it in `evalwire.toml`.
- Check that the delimiter matches `delimiter` (default: `"|"`). If your values contain pipes for other reasons, choose a different delimiter and set `--delimiter`.
- Rows with an empty tag cell are skipped silently.

**`expected_output` is not parsed correctly.**

The `_parse_expected` helper uses `ast.literal_eval` on string values. This means numeric-looking strings like `"0"` or `"1.5"` are converted to Python numeric types (`0`, `1.5`), which can cause type mismatches in string-based evaluators. Use distinct string values for expected outputs when possible.

## "At least one evaluator is required"

Phoenix raises this when `run_experiment` is called with an empty evaluator list. Make sure each experiment directory contains at least one `.py` file (other than `task.py`) that defines a callable matching the filename.

## Experiment name conflicts

Phoenix experiment names include a timestamp, so duplicate names are unlikely. If you need to re-run the same experiment, the old results are preserved and the new run appears alongside it in the UI.
