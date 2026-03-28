"""upload.py — Phase 1: upload the demo testset to Phoenix.

Usage
-----
    python demo/upload.py [--on-exist {skip|overwrite|append}]

Environment variables
---------------------
    PHOENIX_BASE_URL   Base URL of the Phoenix instance (default: http://localhost:6006)
    PHOENIX_API_KEY    API key if Phoenix is running in authenticated mode (optional)
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_DEMO_DIR = Path(__file__).resolve().parent
_CSV_PATH = _DEMO_DIR / "data" / "testset.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload demo testset to Phoenix.")
    parser.add_argument(
        "--on-exist",
        choices=["skip", "overwrite", "append"],
        default="skip",
        help="How to handle datasets that already exist in Phoenix (default: skip).",
    )
    args = parser.parse_args()

    from demo.utils import make_phoenix_client

    client = make_phoenix_client()

    from evalwire import DatasetUploader

    uploader = DatasetUploader(
        csv_path=_CSV_PATH,
        phoenix_client=client,
        input_keys=["user_query"],
        output_keys=["expected_output"],
        tag_column="tags",
        delimiter="|",
    )

    results = uploader.upload(on_exist=args.on_exist)

    for name, dataset in results.items():
        print(f"  [{name}] id={getattr(dataset, 'id', '?')}")

    print(f"\nDone — {len(results)} dataset(s) uploaded.")


if __name__ == "__main__":
    main()
