"""evalwire.toml configuration loader."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and return the evalwire configuration.

    Reads ``evalwire.toml`` from ``config_path`` (or ``./evalwire.toml`` if
    not provided). Returns an empty dict if the file does not exist.

    Parameters
    ----------
    config_path:
        Explicit path to the TOML config file. Defaults to ``./evalwire.toml``.

    Returns
    -------
    dict[str, Any]
        Parsed TOML content, or ``{}`` if the file is absent.
    """
    path = Path(config_path) if config_path else Path("evalwire.toml")

    if not path.exists():
        return {}

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib  # ty: ignore[unresolved-import]

    with path.open("rb") as fh:
        return tomllib.load(fh)


def get_dataset_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the ``[dataset]`` section, or ``{}``."""
    return config.get("dataset", {})


def get_experiments_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the ``[experiments]`` section, or ``{}``."""
    return config.get("experiments", {})


def get_phoenix_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the ``[phoenix]`` section, or ``{}``."""
    return config.get("phoenix", {})
