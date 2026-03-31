# evalwire

**evalwire** is a Python package for systematic evaluation of [LangGraph](https://github.com/langchain-ai/langgraph) nodes using [Arize Phoenix](https://github.com/Arize-ai/phoenix) experiments.

## Features

- Upload CSV testsets to Phoenix as named datasets
- Run experiments against any LangGraph node with pluggable evaluators
- 9 built-in evaluator factories covering retrieval, classification, string matching, structured output, numeric, and LLM-as-a-judge use cases
- OpenTelemetry tracing via `observability.py`
- Config-file driven via `evalwire.toml`
- CLI: `evalwire upload` and `evalwire run`

## Built-in evaluators

| Factory | Returns | Use case |
|---|---|---|
| `make_top_k_evaluator` | `float` | Position-weighted retrieval scoring |
| `make_membership_evaluator` | `bool` | Classification / routing label check |
| `make_exact_match_evaluator` | `bool` | Extractive QA, single ground-truth string |
| `make_contains_evaluator` | `bool` | Free-text generation, required phrase |
| `make_regex_evaluator` | `bool` | Structured format validation (dates, IDs, …) |
| `make_json_match_evaluator` | `float` | Tool-call / structured-output key matching |
| `make_schema_evaluator` | `bool` | JSON Schema conformance |
| `make_numeric_tolerance_evaluator` | `bool` | Math / calculation tasks with tolerance |
| `make_llm_judge_evaluator` | `float \| bool` | LLM-as-a-judge with structured output |

## Navigation

- [Quick Start](quick-start.md) — get up and running in minutes
- [API Reference](api/index.md) — full module documentation
