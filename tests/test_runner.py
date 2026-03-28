"""Tests for evalwire.runner.ExperimentRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from evalwire.runner import ExperimentRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runner(
    experiments_dir: Path, client: MagicMock, **kwargs
) -> ExperimentRunner:
    return ExperimentRunner(
        experiments_dir=experiments_dir,
        phoenix_client=client,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# _discover
# ---------------------------------------------------------------------------


class TestDiscover:
    def test_discovers_both_experiments(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        found = runner._discover(None)
        names = [name for name, _, _ in found]
        assert "es_search" in names
        assert "source_router" in names

    def test_discover_skips_dir_without_task_py(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        (base / "no_task").mkdir()  # no task.py
        runner = _make_runner(base, mock_phoenix_client)
        found = runner._discover(None)
        assert found == []

    def test_discover_filters_by_name(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        found = runner._discover(["es_search"])
        names = [name for name, _, _ in found]
        assert names == ["es_search"]

    def test_discover_returns_empty_for_nonexistent_dir(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(tmp_path / "nonexistent", mock_phoenix_client)
        assert runner._discover(None) == []

    def test_evaluators_loaded_for_experiment(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        found = runner._discover(None)
        by_name = {name: evs for name, _, evs in found}
        assert len(by_name["es_search"]) == 1
        assert len(by_name["source_router"]) == 1

    def test_task_py_without_task_attr_is_skipped(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "bad_task"
        exp.mkdir()
        (exp / "task.py").write_text("# no task callable\n")
        runner = _make_runner(base, mock_phoenix_client)
        found = runner._discover(None)
        assert found == []

    def test_evaluator_without_matching_callable_is_skipped(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "partial"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'x'\n")
        # Evaluator file name is "my_eval.py" but exports "wrong_name"
        (exp / "my_eval.py").write_text("def wrong_name(o, e): return 1.0\n")
        runner = _make_runner(base, mock_phoenix_client)
        found = runner._discover(None)
        assert len(found) == 1
        _, _, evaluators = found[0]
        assert evaluators == []


# ---------------------------------------------------------------------------
# _load_attribute
# ---------------------------------------------------------------------------


class TestLoadAttribute:
    def test_loads_named_attribute(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        py_file = tmp_path / "mymod.py"
        py_file.write_text("VALUE = 42\n")
        runner = _make_runner(tmp_path, mock_phoenix_client)
        result = runner._load_attribute(py_file, "VALUE")
        assert result == 42

    def test_returns_none_for_missing_attribute(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        py_file = tmp_path / "mymod2.py"
        py_file.write_text("x = 1\n")
        runner = _make_runner(tmp_path, mock_phoenix_client)
        result = runner._load_attribute(py_file, "nonexistent")
        assert result is None

    def test_returns_none_on_import_error(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        py_file = tmp_path / "broken.py"
        py_file.write_text("raise ValueError('boom')\n")
        runner = _make_runner(tmp_path, mock_phoenix_client)
        result = runner._load_attribute(py_file, "anything")
        assert result is None


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_calls_run_experiment_for_each_discovered(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        results = runner.run()
        assert mock_phoenix_client.experiments.run_experiment.call_count == 2
        assert len(results) == 2

    def test_run_passes_dry_run_flag(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client, dry_run=3)
        runner.run()
        for c in mock_phoenix_client.experiments.run_experiment.call_args_list:
            assert c.kwargs.get("dry_run") == 3

    def test_run_uses_custom_prefix(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        runner.run(experiment_name_prefix="ci")
        for c in mock_phoenix_client.experiments.run_experiment.call_args_list:
            assert c.kwargs["experiment_name"].startswith("ci_")

    def test_run_attaches_metadata(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        runner.run(metadata={"branch": "main"})
        for c in mock_phoenix_client.experiments.run_experiment.call_args_list:
            assert c.kwargs["experiment_metadata"]["branch"] == "main"

    def test_run_returns_empty_for_no_experiments(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "empty_experiments"
        base.mkdir()
        runner = _make_runner(base, mock_phoenix_client)
        result = runner.run()
        assert result == []

    def test_run_raises_system_exit_1_when_dataset_missing(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.datasets.get_dataset.side_effect = Exception("not found")
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        with pytest.raises(SystemExit) as exc_info:
            runner.run()
        assert exc_info.value.code == 1

    def test_run_raises_system_exit_1_when_experiment_errors(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.side_effect = RuntimeError(
            "boom"
        )
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        with pytest.raises(SystemExit) as exc_info:
            runner.run()
        assert exc_info.value.code == 1

    def test_run_filters_by_names(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        results = runner.run(names=["es_search"])
        assert mock_phoenix_client.experiments.run_experiment.call_count == 1
        assert len(results) == 1

    def test_experiment_name_includes_dataset_name(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        runner.run(names=["es_search"])
        call_kwargs = mock_phoenix_client.experiments.run_experiment.call_args.kwargs
        assert "es_search" in call_kwargs["experiment_name"]
