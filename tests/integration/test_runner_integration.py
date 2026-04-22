"""Integration tests for evalwire.runner.ExperimentRunner.

These tests run against a real in-memory Phoenix instance and verify the
full experiment lifecycle: dataset lookup, task execution, evaluator scoring,
and result retrieval.
"""

from __future__ import annotations

import textwrap
import uuid
from pathlib import Path

import pandas as pd
import pytest

from evalwire.runner import ExperimentRunner

pytestmark = pytest.mark.integration


def _create_dataset(phoenix_client, name: str) -> None:
    """Create a minimal Phoenix dataset with the given name."""
    df = pd.DataFrame(
        {
            "user_query": ["find parks", "find trails"],
            "expected_output": ["park-url", "trail-url"],
        }
    )
    phoenix_client.datasets.create_dataset(
        dataframe=df,
        name=name,
        input_keys=["user_query"],
        output_keys=["expected_output"],
    )


_DEFAULT_EVALUATOR = {
    "check_output": """\
        def check_output(output, expected):
            return 1.0 if output else 0.0
    """,
}


def _make_experiment(
    base: Path,
    name: str,
    task_body: str = "async def task(example): return 'result'",
    evaluators: dict[str, str] | None = None,
) -> None:
    """Create an experiment directory matching a dataset name."""
    exp_dir = base / name
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "task.py").write_text(textwrap.dedent(task_body))
    for ev_name, ev_body in (evaluators or _DEFAULT_EVALUATOR).items():
        (exp_dir / f"{ev_name}.py").write_text(textwrap.dedent(ev_body))


class TestRunnerLifecycle:
    """Upload datasets, then run experiments against them."""

    def test_dry_run_completes(self, phoenix_client, tmp_path: Path):
        name = f"exp_dry_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
            dry_run=True,
        )
        results = runner.run()
        assert len(results) == 1

    def test_full_run_returns_experiment_results(self, phoenix_client, tmp_path: Path):
        name = f"exp_full_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
        )
        results = runner.run()
        assert len(results) == 1

    def test_run_with_evaluator(self, phoenix_client, tmp_path: Path):
        name = f"exp_eval_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(
            base,
            name,
            evaluators={
                "score": """\
                    def score(output, expected):
                        return 0.5
                """,
            },
        )

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
            dry_run=True,
        )
        results = runner.run()
        assert len(results) == 1

    def test_run_with_name_filter(self, phoenix_client, tmp_path: Path):
        name = f"exp_filter_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
            dry_run=True,
        )
        results = runner.run(names=[name])
        assert len(results) == 1

    def test_nonexistent_dataset_raises_system_exit(
        self, phoenix_client, tmp_path: Path
    ):
        name = f"exp_missing_{uuid.uuid4().hex[:8]}"

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
        )
        with pytest.raises(SystemExit) as exc_info:
            runner.run()
        assert exc_info.value.code == 1

    def test_concurrent_run(self, phoenix_client, tmp_path: Path):
        name = f"exp_conc_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
            concurrency=2,
            dry_run=True,
        )
        results = runner.run()
        assert len(results) == 1

    def test_custom_prefix_and_metadata(self, phoenix_client, tmp_path: Path):
        name = f"exp_meta_{uuid.uuid4().hex[:8]}"
        _create_dataset(phoenix_client, name)

        base = tmp_path / "experiments"
        base.mkdir()
        _make_experiment(base, name)

        runner = ExperimentRunner(
            experiments_dir=base,
            phoenix_client=phoenix_client,
            dry_run=True,
        )
        results = runner.run(
            experiment_name_prefix="integ",
            metadata={"ci": True},
        )
        assert len(results) == 1
