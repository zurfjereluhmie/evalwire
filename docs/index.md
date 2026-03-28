# evalwire

**evalwire** is a Python package for systematic evaluation of [LangGraph](https://github.com/langchain-ai/langgraph) nodes using [Arize Phoenix](https://github.com/Arize-ai/phoenix) experiments.

## Features

- Upload CSV testsets to Phoenix as named datasets
- Run experiments against any LangGraph node with pluggable evaluators
- Built-in `top_k` and `membership` evaluators
- OpenTelemetry tracing via `observability.py`
- Config-file driven via `evalwire.toml`
- CLI: `evalwire upload` and `evalwire run`

## Navigation

- [Quick Start](quick-start.md) — get up and running in minutes
- [API Reference](api/index.md) — full module documentation
