# QA Review — evalwire

> Code quality, Python best practices, typing, DRY/KISS, and structural
> observations. Issues are grouped by theme, not file, to surface patterns.
> Severity: **High** (bug risk or correctness), **Medium** (maintainability,
> clarity), **Low** (style, convention).

---

## 1. Exception Handling

### 1.1 Bare `except Exception` swallows all errors (High)

**Files:** `src/evalwire/uploader.py:138-158`

```python
# on_exist == "append"
try:
    self.client.get_dataset(name=name)
    ...
except Exception:
    logger.debug("Dataset %r not found for append; creating it instead.", name)

# on_exist == "skip"
try:
    existing = self.client.get_dataset(name=name)
    ...
except Exception:
    pass  # does not exist yet — fall through to upload
```

Catching bare `Exception` treats every possible failure — network timeout,
authentication error, rate-limit, serialization bug — identically to "dataset
not found". The user sees a silent fallback to `upload_dataset` when the real
cause may be a misconfigured endpoint or missing credentials. This masks
operational errors that should surface immediately.

**Best practice:** Catch the narrowest exception the Phoenix client raises for
"not found" (e.g. `phoenix.exceptions.NotFound` or an HTTP 404 wrapper).
If the client does not expose a typed exception, at minimum log at `WARNING`
level with `exc_info=True` before falling through.

### 1.2 `_load_attribute` silences import errors completely (Medium)

**File:** `src/evalwire/runner.py:173-186`

```python
except Exception as exc:
    logger.error("Failed to load %s: %s", path, exc)
    return None
```

An experiment file with a syntax error, a missing import, or a runtime
exception during module-level code returns `None`, and the experiment is
silently skipped. The error is logged at `ERROR` but execution continues
normally. This can make debugging task failures very opaque.

**Best practice:** Consider re-raising after logging, or — at minimum — emit
the full traceback (`logger.error(..., exc_info=True)`) so the stack trace is
visible in logs.

---

## 2. Dead Code / Unused Parameters

### 2.1 `concurrency` is stored but never used (High)

**File:** `src/evalwire/runner.py:43-46`

```python
self.concurrency = concurrency
```

After assignment in `__init__`, `self.concurrency` is never referenced in the
`run()` method. Experiments always execute sequentially. The public API
promises parallel execution; the implementation delivers none. This is a
silent no-op that could mislead users trying to speed up long evaluation runs.

**Fix:** Implement parallel execution with `concurrent.futures.ThreadPoolExecutor`
(or `asyncio.gather` if moving to async), or remove the parameter and raise a
`NotImplementedError` with a clear message until it is implemented.

---

## 3. Typing

### 3.1 `setup_observability` return type is `Any` (Medium)

**File:** `src/evalwire/observability.py:10`

```python
def setup_observability(...) -> Any:
```

The spec and docstring both state the return type is `TracerProvider`. Using
`Any` disables type-checker inference for all call sites. Because `phoenix` is
a required dependency, the import can be guarded with `TYPE_CHECKING`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider

def setup_observability(...) -> "TracerProvider":
    ...
```

### 3.2 `build_subgraph` return type is `Any` (Medium)

**File:** `src/evalwire/langgraph.py:16`

```python
def build_subgraph(...) -> Any:
```

The spec mandates `-> CompiledStateGraph`. Because `langgraph` is an optional
extra, the import must be guarded, but the annotation can still be expressed
precisely:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

def build_subgraph(...) -> "CompiledStateGraph":
    ...
```

This preserves the typed contract at the call site without requiring `langgraph`
at import time.

### 3.3 `phoenix_client` typed as `Any` everywhere (Medium)

**Files:** `src/evalwire/uploader.py:40`, `src/evalwire/runner.py:38`

```python
phoenix_client: Any,
```

`phoenix.client.Client` is a concrete class from a required dependency.
Typing it as `Any` gives callers no IDE completion, no type-safety, and no
documentation. Use the real type:

```python
from phoenix.client import Client

def __init__(self, ..., phoenix_client: Client, ...) -> None:
```

If a `TYPE_CHECKING` guard is needed to avoid circular imports, use the
string form.

### 3.4 `metadata: dict | None` is under-specified (Low)

**File:** `src/evalwire/runner.py:53`

```python
metadata: dict | None = None,
```

`dict` without type parameters is equivalent to `dict[Any, Any]`. Prefer
`dict[str, Any]` which accurately reflects the intent (string keys, arbitrary
values) and gives type checkers more to work with.

### 3.5 `client_kwargs: dict` in demo scripts is untyped (Low)

**Files:** `demo/upload.py:53`, `demo/run.py:72`

```python
client_kwargs: dict = {"endpoint": base_url}
```

Should be `dict[str, Any]` for the same reason as above.

### 3.6 `example` parameter in task callables is untyped (Low)

**Files:** `demo/experiments/rag_pipeline/task.py:37`,
`tests/conftest.py:99, 114`

```python
async def task(example) -> list[str]:
```

The spec states the signature is `(Example) -> Any` where `Example` is
`phoenix.experiments.types.Example`. Adding the type annotation documents the
contract and enables type-checker validation:

```python
from phoenix.experiments.types import Example

async def task(example: Example) -> list[str]:
```

---

## 4. Structural / Design

### 4.1 Duplicated Phoenix client construction in demo scripts (Medium)

**Files:** `demo/upload.py:50-57`, `demo/run.py:69-76`

The following block is copy-pasted verbatim in both scripts:

```python
base_url = os.environ.get("PHOENIX_BASE_URL", "http://localhost:6006")
api_key = os.environ.get("PHOENIX_API_KEY")
client_kwargs: dict = {"endpoint": base_url}
if api_key:
    client_kwargs["api_key"] = api_key
client = px.Client(**client_kwargs)
logging.getLogger(__name__).info("Connected to Phoenix at %s", base_url)
```

This violates DRY. A shared `demo/utils.py` (or a top-level `demo/__init__.py`)
with a `make_phoenix_client() -> px.Client` helper would eliminate the
duplication and make it easier to add retry logic, logging, or env-var
validation in one place.

### 4.2 LLM instantiated on every `generate` call (Medium)

**File:** `demo/agent/graph.py:131`

```python
def generate(state: RAGState) -> dict:
    llm = init_chat_model("gpt-4.1-mini", model_provider="openai")
    ...
```

`init_chat_model` is called for every example in the dataset, creating a new
client object each time. This is unnecessary overhead and could exhaust
connection pools under load. The LLM should be instantiated once at module
level or in `build_rag_graph()` via closure:

```python
_LLM = init_chat_model("gpt-4.1-mini", model_provider="openai")

def generate(state: RAGState) -> dict:
    response = _LLM.invoke(...)
```

### 4.3 Module-level subgraph compilation in `task.py` (Medium)

**File:** `demo/experiments/rag_pipeline/task.py:30-34`

```python
_subgraph = build_subgraph(
    nodes=[("retrieve", retrieve)],
    state_cls=RAGState,
    name="retrieve_only",
)
```

This runs at import time. If `langgraph` is not installed, or if `agent.graph`
raises an error, importing `task.py` will crash during experiment discovery
before any useful error message can be shown. It also makes the module harder
to test in isolation.

**Best practice:** Lazy-initialise behind a module-level `None` guard, or use
`functools.lru_cache` on a factory function.

### 4.4 `runner._discover` permanently mutates `sys.path` (Medium)

**File:** `src/evalwire/runner.py:127-129`

```python
parent = str(self.experiments_dir.parent.resolve())
if parent not in sys.path:
    sys.path.insert(0, parent)
```

`sys.path` is modified globally for the lifetime of the process. In a test
suite this leaks across tests; in a long-running process it can cause
unexpected module shadowing. A context manager or a `try/finally` cleanup is
more appropriate:

```python
sys.path.insert(0, parent)
try:
    # discovery
finally:
    sys.path.remove(parent)
```

### 4.5 `_upload_one` control flow mixes early-return and fall-through (Medium)

**File:** `src/evalwire/uploader.py:126-168`

The three `on_exist` branches are implemented as:
- `"append"`: early `try/except` with early `return`, then falls through
- `"skip"`: early `try/except` with early `return`, then falls through
- `"overwrite"`: implicit — falls straight through to `upload_dataset`

All three paths converge on the same `upload_dataset` call but via different
control-flow shapes. This is fragile: adding a fourth mode or changing
fallback logic requires tracing through the branching carefully. A dispatch
table or explicit `if/elif/else` covering all three cases would be clearer:

```python
if on_exist == "skip":
    ...
    return existing
elif on_exist == "append":
    ...
    return dataset
else:  # "overwrite"
    ...
    return self.client.upload_dataset(...)
```

### 4.6 `_load_csv` applies `.astype(str)` twice (Low)

**File:** `src/evalwire/uploader.py:93-105`

```python
mask = df[col].astype(str).str.contains(delimiter, regex=False, na=False)
if mask.any() or col == self.tag_column:
    df[col] = df[col].astype(str).apply(...)
```

`.astype(str)` is called twice for the same column. The second call is
necessary (to handle non-string dtypes), but the result of the first call
could be reused:

```python
as_str = df[col].astype(str)
mask = as_str.str.contains(delimiter, regex=False, na=False)
if mask.any() or col == self.tag_column:
    df[col] = as_str.apply(...)
```

---

## 5. KISS / Complexity

### 5.1 `runner._load_attribute` is unnecessarily low-level (Medium)

**File:** `src/evalwire/runner.py:173-186`

`importlib.util.spec_from_file_location` + `module_from_spec` + `exec_module`
is the low-level imperative API. For this use case — loading a file by path
and retrieving a named attribute — a small wrapper using `importlib.import_module`
after temporarily inserting the parent directory on `sys.path` is more readable.
Alternatively, since Python 3.5+ the pattern is well-established; a comment
explaining *why* the low-level API is used (e.g., to avoid polluting the
package namespace) would reduce cognitive overhead for maintainers.

### 5.2 `build_subgraph` edge-wiring loop can be simplified (Low)

**File:** `src/evalwire/langgraph.py:62-69`

```python
for i, node_name in enumerate(node_names):
    if i == 0:
        graph.add_edge(START, node_name)
    if i < len(node_names) - 1:
        graph.add_edge(node_name, node_names[i + 1])
    else:
        graph.add_edge(node_name, END)
```

Using `zip` to pair consecutive nodes is more Pythonic and eliminates the
index arithmetic:

```python
graph.add_edge(START, node_names[0])
for a, b in zip(node_names, node_names[1:]):
    graph.add_edge(a, b)
graph.add_edge(node_names[-1], END)
```

---

## 6. Tooling / Configuration

### 6.1 `ruff.toml` target-version conflicts with `requires-python` (Medium)

**File:** `ruff.toml:3`

```toml
target-version = "py313"
```

**File:** `pyproject.toml`

```toml
requires-python = ">=3.10"
```

Ruff targets Python 3.13, but the package claims compatibility back to 3.10.
Ruff will not flag syntax or API usage that is invalid on 3.10–3.12. The
`target-version` should match the minimum supported version:

```toml
target-version = "py310"
```

### 6.2 `.python-version` pins 3.13 but `requires-python` allows ≥3.10 (Low)

**File:** `.python-version`

```
3.13
```

This is fine for development, but CI should also test against 3.10 (the stated
minimum) to catch accidental use of 3.11+ stdlib features without a
`sys.version_info` guard (e.g., the `tomllib` guard in `config.py` is correct,
but `match` statements or `ExceptionGroup` would not be caught by running only
on 3.13).

### 6.3 `ty` is used for type checking but is pre-release (Low)

**Files:** `.pre-commit-config.yaml`, `Makefile`, `pyproject.toml`

`ty` (Astral's new type checker, `ty>=0.0.26`) is used in the pre-commit
hook and `make typecheck`. As of early 2026, `ty` is still in early
development and its diagnostics are not yet complete. Using it alongside or
instead of `mypy` is a pragmatic choice, but the project should document this
decision and be aware that some type errors (particularly around generics and
protocols) may be missed.

---

## 7. Testing

### 7.1 No async tests for task callables (High)

**Files:** `tests/test_runner.py`, `demo/experiments/rag_pipeline/task.py`

All task functions are `async def`. In tests, they are passed as callables to
the mocked `run_experiment` but never actually awaited. There are zero tests
that exercise the async execution path of any task function. A bug in
`await _subgraph.ainvoke(state)` inside `task.py` would not be caught by the
test suite at all. Add at least one `pytest-asyncio` test per task to verify
the async contract.

### 7.2 Tests mock the flat client API, not the spec API (High)

**Files:** `tests/conftest.py:52-62`, `tests/test_uploader.py`

```python
client.upload_dataset.return_value = created_ds
client.get_dataset.return_value = created_ds
client.append_to_dataset.return_value = created_ds
```

The mock mirrors the flat API used in the implementation, not the namespaced
API specified in the spec (`client.datasets.*`). Because both the
implementation and the mock are wrong in the same way, all uploader tests
pass. This is a false-positive test suite: it validates internal consistency
but not correctness against the real Phoenix 13.x API.

### 7.3 No integration / smoke test against a real Phoenix instance (Medium)

There are no tests that run against a real (or Docker-based) Phoenix server.
The `demo/docker-compose.yml` sets up Phoenix, but there is no corresponding
integration test suite. A single smoke test (upload → run → assert experiment
exists) would catch API surface mismatches that unit tests with mocks cannot.

### 7.4 `conftest.py` `sample_df` fixture is unused by any test (Low)

**File:** `tests/conftest.py:25-42`

The `sample_df` fixture is defined but never referenced in any test file.
Unused fixtures add noise and maintenance surface. Remove it or add a test
that exercises a code path accepting a pre-parsed DataFrame.

---

## 8. Documentation & Docstrings

### 8.1 `config.py` functions have no docstrings (Low)

**File:** `src/evalwire/config.py`

`get_dataset_config`, `get_experiments_config`, and `get_phoenix_config` are
public API functions with no docstrings. The mkdocstrings page at
`docs/api/config.md` will render empty sections for them. A single-line
docstring per function is sufficient.

### 8.2 `cli.py` has no module-level docstring for `_make_client` (Low)

**File:** `src/evalwire/cli.py:15-19`

`_make_client` is a private helper with no docstring. Given that it is
responsible for all Phoenix client construction in the CLI layer, a brief
comment explaining why it is lazily imported (to avoid importing Phoenix at
module import time and slowing down `--help`) would be valuable.

### 8.3 `__init__.py` does not export `build_subgraph` or `invoke_node` (Low)

**File:** `src/evalwire/__init__.py`

```python
__all__ = [
    "DatasetUploader",
    "ExperimentRunner",
    "make_membership_evaluator",
    "make_top_k_evaluator",
    "setup_observability",
]
```

`build_subgraph` and `invoke_node` from `evalwire.langgraph` are not re-exported
from the top-level package. Since they are guarded by an optional dependency,
this is defensible, but it means `from evalwire import build_subgraph` fails
even when `langgraph` is installed. Users must know to import from
`evalwire.langgraph` directly. This inconsistency should be documented or the
exports added with a clear note about the optional extra.

---

## 9. Minor Python Style

### 9.1 `demo/agent/graph.py` — `retrieve` hardcodes the fallback to one result (Low)

**File:** `demo/agent/graph.py:124`

```python
top_titles = [title for _, title in scored[:5] if _ > 0] or [scored[0][1]]
```

If all scores are 0 (no keyword overlap at all), the function returns the
first corpus document regardless of relevance. This is a reasonable demo
simplification but should be commented to prevent confusion.

### 9.2 `demo/upload.py` imports `phoenix as px` inside a try/except but then uses it outside (Low)

**File:** `demo/upload.py:43-57`

```python
try:
    import phoenix as px
except ImportError:
    sys.exit(...)

base_url = ...
client = px.Client(...)
```

The pattern is correct but `px` is used well after the `try/except` block. A
reader must scroll up to confirm `px` is defined. Restructuring to import at
the top (with a clear `# requires arize-phoenix` comment) or keeping all `px`
usage inside the `try` block is cleaner.

### 9.3 `retrieve` uses set intersection but splits on whitespace only (Low)

**File:** `demo/agent/graph.py:114`

```python
query_words = set(query.split())
body_words = set(doc["body"].lower().split())
```

`str.split()` splits on whitespace only and preserves punctuation (e.g.
`"football."` ≠ `"football"`). For a demo this is acceptable, but a comment
acknowledging the limitation prevents future maintainers from treating it as
production-quality retrieval.

---

## Summary Table

| # | File(s) | Severity | Category | Description |
|---|---------|----------|----------|-------------|
| 1.1 | `uploader.py` | High | Error handling | Bare `except Exception` swallows network/auth errors |
| 1.2 | `runner.py` | Medium | Error handling | Import errors logged but traceback suppressed |
| 2.1 | `runner.py` | High | Dead code | `concurrency` stored but never used |
| 3.1 | `observability.py` | Medium | Typing | Return type `Any` instead of `TracerProvider` |
| 3.2 | `langgraph.py` | Medium | Typing | Return type `Any` instead of `CompiledStateGraph` |
| 3.3 | `uploader.py`, `runner.py` | Medium | Typing | `phoenix_client: Any` instead of `Client` |
| 3.4 | `runner.py` | Low | Typing | `dict` without type parameters |
| 3.5 | `demo/upload.py`, `demo/run.py` | Low | Typing | `client_kwargs: dict` untyped |
| 3.6 | `demo/…/task.py`, `tests/conftest.py` | Low | Typing | `example` parameter untyped |
| 4.1 | `demo/upload.py`, `demo/run.py` | Medium | DRY | Phoenix client construction duplicated |
| 4.2 | `demo/agent/graph.py` | Medium | Performance | LLM re-instantiated on every call |
| 4.3 | `demo/…/task.py` | Medium | Design | Module-level subgraph compilation at import time |
| 4.4 | `runner.py` | Medium | Side effects | `sys.path` permanently mutated |
| 4.5 | `uploader.py` | Medium | Clarity | `_upload_one` control flow mixes early-return and fall-through |
| 4.6 | `uploader.py` | Low | Performance | `.astype(str)` called twice on same column |
| 5.1 | `runner.py` | Medium | KISS | Low-level `importlib` API undocumented |
| 5.2 | `langgraph.py` | Low | KISS | Edge-wiring loop uses index arithmetic instead of `zip` |
| 6.1 | `ruff.toml` | Medium | Tooling | `target-version = "py313"` mismatches `requires-python = ">=3.10"` |
| 6.2 | `.python-version` | Low | Tooling | Dev env on 3.13; no CI matrix for 3.10–3.12 |
| 6.3 | `pyproject.toml` | Low | Tooling | `ty` is pre-release |
| 7.1 | `tests/` | High | Testing | No async tests for `async def task` callables |
| 7.2 | `tests/conftest.py` | High | Testing | Mocks mirror flat API, not spec API — false-positive tests |
| 7.3 | `tests/` | Medium | Testing | No integration tests against real Phoenix |
| 7.4 | `tests/conftest.py` | Low | Testing | `sample_df` fixture defined but never used |
| 8.1 | `config.py` | Low | Docs | Public functions have no docstrings |
| 8.2 | `cli.py` | Low | Docs | `_make_client` has no docstring/comment |
| 8.3 | `__init__.py` | Low | API | `build_subgraph`/`invoke_node` not exported from top-level package |
| 9.1 | `demo/agent/graph.py` | Low | Style | Hardcoded fallback not commented |
| 9.2 | `demo/upload.py` | Low | Style | `px` used outside `try/except` scope |
| 9.3 | `demo/agent/graph.py` | Low | Style | Whitespace-only tokenisation not documented |
