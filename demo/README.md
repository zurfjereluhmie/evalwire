# evalwire demo

End-to-end demo of the `evalwire` package using a simple LangGraph RAG pipeline,
a self-hosted Phoenix instance, and a human-curated testset.

## What this demo does

1. **Upload** — reads `data/testset.csv` and creates one Phoenix dataset per unique
   tag value (`rag_pipeline`).
2. **Run** — for each Phoenix dataset, isolates the `retrieve` node of the RAG
   graph, scores every example with a position-weighted top-K evaluator, and
   records traces in Phoenix via OpenTelemetry.

## Prerequisites

- Docker and Docker Compose
- Python ≥ 3.10
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Step 1 — Start Phoenix

```bash
docker compose -f demo/docker-compose.yml up -d
```

Phoenix will be available at <http://localhost:6006>.
Data is persisted in a named Docker volume (`phoenix_data`).

## Step 2 — Install dependencies

From the repository root:

```bash
# Install the evalwire package together with all demo dependencies
# (LangChain, LangGraph, OpenAI, OpenInference tracing).
uv sync --group demo
```

## Step 3 — Configure environment variables

```bash
cp demo/.env.example demo/.env
# Edit demo/.env and set OPENAI_API_KEY to your key.
```

`run.py` loads `demo/.env` automatically via `python-dotenv` — no manual `export` needed.

## Step 4 — Upload the testset

```bash
python demo/upload.py
# Use --on-exist overwrite to replace existing datasets.
```

## Step 5 — Run the experiments

```bash
python demo/run.py
# Use --dry-run to test with only the first example per experiment.
# Use --experiment rag_pipeline to run a specific experiment by name.
```

## Step 6 — Inspect results in Phoenix

Open <http://localhost:6006> → **Datasets** → **rag_pipeline** → **Experiments**
to view per-example scores and LLM traces.

## Directory structure

```
demo/
├── docker-compose.yml          # Phoenix service + persistent volume
├── .env.example                # Environment variable template
├── upload.py                   # Phase 1: upload testset to Phoenix
├── run.py                      # Phase 2: run experiments + emit traces
├── data/
│   └── testset.csv             # 14 human-curated topic-routing queries
├── agent/
│   └── graph.py                # LangGraph RAG pipeline (retrieve → generate)
└── experiments/
    └── rag_pipeline/
        ├── task.py             # Isolates the retrieve node; returns titles
        └── top_k.py            # Position-weighted top-5 evaluator
```
