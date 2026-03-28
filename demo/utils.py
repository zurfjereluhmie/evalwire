"""Shared utilities for evalwire demo scripts."""

import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


def make_phoenix_client() -> Any:
    """Construct a Phoenix client from environment variables.

    Reads ``PHOENIX_BASE_URL`` (default: ``http://localhost:6006``) and
    ``PHOENIX_API_KEY`` (optional) from the environment.

    Returns
    -------
    phoenix.Client
        An initialised Phoenix client ready to use.
    """
    try:
        import phoenix as px
    except ImportError:
        sys.exit(
            "arize-phoenix is not installed. "
            "Run: pip install 'evalwire[all]' or pip install arize-phoenix"
        )

    base_url = os.environ.get("PHOENIX_BASE_URL", "http://localhost:6006")
    api_key = os.environ.get("PHOENIX_API_KEY")

    client_kwargs: dict[str, Any] = {"endpoint": base_url}
    if api_key:
        client_kwargs["api_key"] = api_key

    client = px.Client(**client_kwargs)
    logger.info("Connected to Phoenix at %s", base_url)
    return client
