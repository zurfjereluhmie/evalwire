"""run.py — Phase 2: run experiments against Phoenix datasets and emit traces.

Usage
-----
    python demo/run.py [--dry-run] [--experiment NAMES...]

Environment variables
---------------------
    OPENAI_API_KEY     Required — passed through to the LangChain LLM call.
    PHOENIX_BASE_URL   Base URL of the Phoenix instance (default: http://localhost:6006)
    PHOENIX_API_KEY    API key if Phoenix is running in authenticated mode (optional)

A ``.env`` file in the demo directory (or any parent) is loaded automatically
via ``python-dotenv`` before the environment is read.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_DEMO_DIR = Path(__file__).resolve().parent
_EXPERIMENTS_DIR = _DEMO_DIR / "experiments"

# Load .env from the demo directory (falls back to any parent .env automatically).
load_dotenv(_DEMO_DIR / ".env")


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

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set. Export it before running this script.")

    from demo.utils import make_phoenix_client

    client = make_phoenix_client()

    from evalwire import setup_observability

    setup_observability(auto_instrument=True)

    from evalwire import ExperimentRunner

    runner = ExperimentRunner(
        experiments_dir=_EXPERIMENTS_DIR,
        phoenix_client=client,
        dry_run=args.dry_run,
    )

    results = runner.run(names=args.experiments)
    print(f"\nDone — {len(results)} experiment(s) completed.")
    base_url = os.environ.get("PHOENIX_BASE_URL", "http://localhost:6006")
    print("Open Phoenix at", base_url, "to view results.")


if __name__ == "__main__":
    main()
