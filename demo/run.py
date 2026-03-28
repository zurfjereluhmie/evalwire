"""run.py — Phase 2: run experiments against Phoenix datasets and emit traces.

Usage
-----
    python demo/run.py [--dry-run] [--experiment NAMES...]

Environment variables
---------------------
    OPENAI_API_KEY     Required — passed through to the LangChain LLM call.
    PHOENIX_BASE_URL   Base URL of the Phoenix instance (default: http://localhost:6006)
    PHOENIX_API_KEY    API key if Phoenix is running in authenticated mode (optional)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_DEMO_DIR = Path(__file__).resolve().parent
_EXPERIMENTS_DIR = _DEMO_DIR / "experiments"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run evalwire experiments against Phoenix."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run only the first example per experiment (no results uploaded).",
    )
    parser.add_argument(
        "--experiment",
        metavar="NAME",
        nargs="+",
        dest="experiments",
        help="Experiment names to run (default: all discovered).",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate environment
    # ------------------------------------------------------------------
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set. Export it before running this script.")

    # ------------------------------------------------------------------
    # Build Phoenix client
    # ------------------------------------------------------------------
    try:
        import phoenix as px
    except ImportError:
        sys.exit(
            "arize-phoenix is not installed. "
            "Run: pip install 'evalwire[all]' or pip install arize-phoenix"
        )

    base_url = os.environ.get("PHOENIX_BASE_URL", "http://localhost:6006")
    api_key = os.environ.get("PHOENIX_API_KEY")

    client_kwargs: dict = {"endpoint": base_url}
    if api_key:
        client_kwargs["api_key"] = api_key

    client = px.Client(**client_kwargs)
    logging.getLogger(__name__).info("Connected to Phoenix at %s", base_url)

    # ------------------------------------------------------------------
    # Register Phoenix as the OTel tracer provider so that LLM calls
    # made inside the task are traced and appear in the Phoenix UI.
    # ------------------------------------------------------------------
    from evalwire import setup_observability

    setup_observability(auto_instrument=True)

    # ------------------------------------------------------------------
    # Run experiments
    # ------------------------------------------------------------------
    from evalwire import ExperimentRunner

    runner = ExperimentRunner(
        experiments_dir=_EXPERIMENTS_DIR,
        phoenix_client=client,
        dry_run=args.dry_run,
    )

    results = runner.run(names=args.experiments)
    print(f"\nDone — {len(results)} experiment(s) completed.")
    print("Open Phoenix at", base_url, "to view results.")


if __name__ == "__main__":
    main()
