"""Shared fixtures for integration tests.

These tests spin up an in-memory Phoenix server per session and create a
real ``phoenix.client.Client`` connected to it.  They are gated behind
the ``integration`` marker so they can be skipped in fast CI runs::

    pytest -m integration          # run only integration tests
    pytest -m 'not integration'    # skip integration tests (default)
"""

from __future__ import annotations

import os
import socket
import textwrap
import uuid
from pathlib import Path

import pytest


def _find_free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _unique_tag() -> str:
    """Return a short unique suffix for dataset names."""
    return uuid.uuid4().hex[:8]


@pytest.fixture(scope="session")
def phoenix_server():
    """Launch an in-memory Phoenix instance for the entire test session.

    Yields the session URL (e.g. ``http://localhost:54321``).
    Cleans up the server and all data after the session ends.
    """
    import phoenix as px

    port = _find_free_port()
    px.launch_app(run_in_thread=True, use_temp_dir=True, port=port)
    url = f"http://localhost:{port}"

    yield url

    px.close_app(delete_data=True)


@pytest.fixture()
def phoenix_client(phoenix_server: str):
    """Return a ``phoenix.client.Client`` connected to the test server.

    Sets ``PHOENIX_COLLECTOR_ENDPOINT`` so that code which creates its own
    ``Client()`` (like ``evalwire.cli._make_client``) also points at the
    test instance.
    """
    from phoenix.client import Client

    old = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = phoenix_server

    client = Client()

    yield client

    # Restore original env
    if old is None:
        os.environ.pop("PHOENIX_COLLECTOR_ENDPOINT", None)
    else:
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = old


@pytest.fixture()
def integration_csv(tmp_path: Path) -> tuple[Path, str, str]:
    """Write a small CSV testset with unique tag names.

    Returns ``(csv_path, search_tag, router_tag)`` so tests can reference
    the unique dataset names.
    """
    tag = _unique_tag()
    search_tag = f"search_{tag}"
    router_tag = f"router_{tag}"

    content = textwrap.dedent(f"""\
        user_query,expected_output,tags
        "find cycling paths","url-a | url-b","{search_tag} | {router_tag}"
        "find parks","url-c","{search_tag}"
        "route me home","home","{router_tag}"
    """)
    csv_file = tmp_path / "testset.csv"
    csv_file.write_text(content)
    return csv_file, search_tag, router_tag


@pytest.fixture()
def integration_experiments(tmp_path: Path) -> tuple[Path, str]:
    """Create a minimal experiments/ directory for integration testing.

    Returns ``(experiments_dir, experiment_name)`` where *experiment_name*
    is the unique dataset-matching directory name.
    """
    tag = _unique_tag()
    exp_name = f"exp_{tag}"

    base = tmp_path / "experiments"
    base.mkdir()

    exp_dir = base / exp_name
    exp_dir.mkdir()
    (exp_dir / "task.py").write_text(
        textwrap.dedent("""\
            async def task(example):
                return example.input.get("user_query", "") + " result"
        """)
    )
    (exp_dir / "check_output.py").write_text(
        textwrap.dedent("""\
            def check_output(output, expected):
                return 1.0 if output else 0.0
        """)
    )

    return base, exp_name
