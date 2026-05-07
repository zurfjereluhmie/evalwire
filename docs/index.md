# evalwire

**evalwire** is a Python package for systematic evaluation of any async callable — including [LangGraph](https://github.com/langchain-ai/langgraph) nodes, plain functions, REST API endpoints, and other LLM frameworks — using [Arize Phoenix](https://github.com/Arize-ai/phoenix) experiments.

## Features

- Upload CSV testsets to Phoenix as named datasets
- Run experiments against any async callable with pluggable evaluators
- 12 built-in evaluator factories covering retrieval, classification, string matching, structured output, numeric, LLM-as-a-judge, and evaluator composition
- Export experiment results to CSV or JSON, compare runs, and generate markdown reports
- Validate testsets before upload to catch structural and content issues early
- First-class LangGraph integration via the optional `evalwire[langgraph]` extra
- OpenTelemetry tracing via `observability.py`
- Config-file driven via `evalwire.toml`
- CLI: `evalwire upload`, `evalwire run`, `evalwire validate`, `evalwire export`, `evalwire compare`, `evalwire report`

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
| `make_weighted_evaluator` | `float` | Weighted average of multiple evaluators |
| `make_all_pass_evaluator` | `bool` | AND-composition: all evaluators must pass |
| `make_any_pass_evaluator` | `bool` | OR-composition: at least one evaluator must pass |

## Navigation

- [Quick Start](quick-start.md): get up and running in minutes
- [Concepts](concepts.md): understand datasets, experiments, tasks, and evaluators
- [Guides: Writing Custom Evaluators](guides/custom-evaluators.md): evaluator contract, patterns, and best practices
- [Configuration](configuration.md): full `evalwire.toml` reference
- [Troubleshooting](troubleshooting.md): common errors and fixes
- [API Reference](api/index.md): full module documentation
- [Changelog](changelog.md): version history
