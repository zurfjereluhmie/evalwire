"""Shared pytest fixtures for the evalwire test suite."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """A minimal CSV testset with two tags and two rows."""
    content = textwrap.dedent("""\
        user_query,expected_output,tags
        "find cycling paths","url-a | url-b","es_search | source_router"
        "find parks","url-c","es_search"
        "route me home","home","source_router"
    """)
    csv_file = tmp_path / "testset.csv"
    csv_file.write_text(content)
    return csv_file


def _make_dataset_mock(name: str, id_: str = "ds-1") -> MagicMock:
    ds = MagicMock()
    ds.id = id_
    ds.name = name
    return ds


@pytest.fixture()
def mock_phoenix_client() -> MagicMock:
    """A MagicMock that mimics the namespaced API of ``phoenix.Client`` (>=13)."""
    client = MagicMock()

    created_ds = _make_dataset_mock("es_search")
    client.datasets.create_dataset.return_value = created_ds
    client.datasets.get_dataset.return_value = created_ds
    client.datasets.delete_dataset.return_value = None
    client.datasets.add_examples.return_value = created_ds

    return client


def _write_experiment(
    base: Path,
    name: str,
    task_body: str,
    evaluators: dict[str, str] | None = None,
) -> Path:
    """Create an experiment subdirectory with task.py and optional evaluator files."""
    exp_dir = base / name
    exp_dir.mkdir(parents=True, exist_ok=True)

    (exp_dir / "task.py").write_text(
        textwrap.dedent(task_body),
        encoding="utf-8",
    )

    for ev_name, ev_body in (evaluators or {}).items():
        (exp_dir / f"{ev_name}.py").write_text(
            textwrap.dedent(ev_body),
            encoding="utf-8",
        )

    return exp_dir


@pytest.fixture()
def experiments_dir(tmp_path: Path) -> Path:
    """An experiments/ directory pre-populated with two valid experiments."""
    base = tmp_path / "experiments"
    base.mkdir()

    _write_experiment(
        base,
        "es_search",
        task_body="""\
            async def task(example):
                return ["url-a", "url-b", "url-c"]
        """,
        evaluators={
            "top_k": """\
                def top_k(output, expected):
                    return 1.0
            """
        },
    )

    _write_experiment(
        base,
        "source_router",
        task_body="""\
            async def task(example):
                return "es_search"
        """,
        evaluators={
            "is_in": """\
                def is_in(output, expected):
                    return True
            """
        },
    )

    return base
