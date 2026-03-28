"""evalwire CLI — ``evalwire upload`` and ``evalwire run`` commands."""

from __future__ import annotations

import sys
from typing import Literal, cast

import click

from evalwire.config import (
    get_dataset_config,
    get_experiments_config,
    load_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client():
    """Instantiate and return a Phoenix client."""
    from phoenix.client import Client

    return Client()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def main() -> None:
    """evalwire — systematic evaluation of LangGraph nodes with Arize Phoenix."""


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------


@main.command("upload")
@click.option("--csv", "csv_path", default=None, help="Path to the CSV file.")
@click.option(
    "--on-exist",
    type=click.Choice(["skip", "overwrite", "append"]),
    default=None,
    show_default=True,
    help="How to handle existing datasets.",
)
@click.option(
    "--input-keys",
    default=None,
    help="Comma-separated input column names.",
)
@click.option(
    "--output-keys",
    default=None,
    help="Comma-separated output column names.",
)
@click.option(
    "--tag-column",
    default=None,
    help="Column used for dataset splitting.",
)
@click.option(
    "--delimiter",
    default=None,
    help="Pipe-split delimiter.",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to evalwire.toml.",
)
def upload_cmd(
    csv_path: str | None,
    on_exist: str | None,
    input_keys: str | None,
    output_keys: str | None,
    tag_column: str | None,
    delimiter: str | None,
    config_path: str | None,
) -> None:
    """Upload a CSV testset to Arize Phoenix as one or more named datasets."""
    try:
        config = load_config(config_path)
        ds_cfg = get_dataset_config(config)

        # CLI flags take precedence over config file values.
        resolved_csv = csv_path or ds_cfg.get("csv_path")
        resolved_on_exist = cast(
            Literal["skip", "overwrite", "append"],
            on_exist or ds_cfg.get("on_exist", "skip"),
        )
        resolved_input_keys = (
            [k.strip() for k in input_keys.split(",")]
            if input_keys
            else ds_cfg.get("input_keys", ["user_query"])
        )
        resolved_output_keys = (
            [k.strip() for k in output_keys.split(",")]
            if output_keys
            else ds_cfg.get("output_keys", ["expected_output"])
        )
        resolved_tag_column = tag_column or ds_cfg.get("tag_column", "tags")
        resolved_delimiter = delimiter or ds_cfg.get("delimiter", "|")

        if not resolved_csv:
            raise click.UsageError(
                "No CSV path provided. Use --csv or set csv_path in evalwire.toml."
            )

        from evalwire.uploader import DatasetUploader

        client = _make_client()
        uploader = DatasetUploader(
            csv_path=resolved_csv,
            phoenix_client=client,
            input_keys=resolved_input_keys,
            output_keys=resolved_output_keys,
            tag_column=resolved_tag_column,
            delimiter=resolved_delimiter,
        )
        datasets = uploader.upload(on_exist=resolved_on_exist)
        click.echo(f"Uploaded {len(datasets)} dataset(s): {', '.join(datasets)}")
    except click.UsageError:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@main.command("run")
@click.option(
    "--experiments",
    "experiments_path",
    default=None,
    help="Path to the experiments directory.",
)
@click.option(
    "--name",
    "names",
    multiple=True,
    help="Run only the named experiment(s). Repeatable.",
)
@click.option(
    "--dry-run",
    "dry_run",
    default=None,
    type=int,
    is_flag=False,
    flag_value=1,
    help="Run without uploading results. Optional count of examples.",
)
@click.option(
    "--concurrency",
    default=None,
    type=int,
    help="Number of parallel experiments.",
)
@click.option(
    "--prefix",
    default=None,
    help="Experiment name prefix in Phoenix.",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to evalwire.toml.",
)
def run_cmd(
    experiments_path: str | None,
    names: tuple[str, ...],
    dry_run: int | None,
    concurrency: int | None,
    prefix: str | None,
    config_path: str | None,
) -> None:
    """Discover and execute all registered experiments against their Phoenix datasets."""
    try:
        config = load_config(config_path)
        exp_cfg = get_experiments_config(config)

        resolved_experiments_path = experiments_path or exp_cfg.get(
            "dir", "experiments"
        )
        resolved_concurrency = (
            concurrency if concurrency is not None else exp_cfg.get("concurrency", 1)
        )
        resolved_prefix = prefix or exp_cfg.get("prefix", "eval")
        resolved_dry_run: bool | int = dry_run if dry_run is not None else False

        from evalwire.runner import ExperimentRunner

        client = _make_client()
        runner = ExperimentRunner(
            experiments_dir=resolved_experiments_path,
            phoenix_client=client,
            concurrency=resolved_concurrency,
            dry_run=resolved_dry_run,
        )
        results = runner.run(
            names=list(names) if names else None,
            experiment_name_prefix=resolved_prefix,
        )
        click.echo(f"Completed {len(results)} experiment(s).")
    except SystemExit:
        sys.exit(1)
    except click.UsageError:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
