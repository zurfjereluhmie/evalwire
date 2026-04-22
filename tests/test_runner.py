"""Tests for evalwire.runner.ExperimentRunner."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from evalwire.runner import ExperimentRunner


def _make_runner(
    experiments_dir: Path, client: MagicMock, **kwargs
) -> ExperimentRunner:
    return ExperimentRunner(
        experiments_dir=experiments_dir,
        phoenix_client=client,
        **kwargs,
    )


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
        (base / "no_task").mkdir()
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

    def test_discover_creates_missing_init_py(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "my_exp"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'x'\n")
        assert not (exp / "__init__.py").exists()
        runner = _make_runner(base, mock_phoenix_client)
        runner._discover(None)
        assert (exp / "__init__.py").exists()

    def test_discover_does_not_overwrite_existing_init_py(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "my_exp"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'x'\n")
        (exp / "__init__.py").write_text("# existing\n")
        runner = _make_runner(base, mock_phoenix_client)
        runner._discover(None)
        assert (exp / "__init__.py").read_text() == "# existing\n"

    def test_evaluator_without_matching_callable_is_skipped(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "partial"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'x'\n")
        (exp / "my_eval.py").write_text("def wrong_name(o, e): return 1.0\n")
        runner = _make_runner(base, mock_phoenix_client)
        found = runner._discover(None)
        assert len(found) == 1
        _, _, evaluators = found[0]
        assert evaluators == []


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

    def test_cleans_sys_modules_on_import_error(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        """A broken module must not leak into sys.modules."""
        import sys

        py_file = tmp_path / "leaky.py"
        py_file.write_text("raise RuntimeError('kaboom')\n")
        runner = _make_runner(tmp_path, mock_phoenix_client)
        module_name = f"_evalwire_exp_{py_file.parent.name}_{py_file.stem}"

        result = runner._load_attribute(py_file, "anything")
        assert result is None
        assert module_name not in sys.modules


class TestRun:
    def test_run_calls_run_experiment_for_each_discovered(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        results = runner.run()
        assert mock_phoenix_client.experiments.run_experiment.call_count == 2
        assert len(results) == 2

    def test_run_passes_dry_run_flag(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
        runner = _make_runner(experiments_dir, mock_phoenix_client, dry_run=3)
        runner.run()
        for c in mock_phoenix_client.experiments.run_experiment.call_args_list:
            assert c.kwargs.get("dry_run") == 3

    def test_run_uses_custom_prefix(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        runner.run(experiment_name_prefix="ci")
        for c in mock_phoenix_client.experiments.run_experiment.call_args_list:
            assert c.kwargs["experiment_name"].startswith("ci_")

    def test_run_attaches_metadata(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
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
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        results = runner.run(names=["es_search"])
        assert mock_phoenix_client.experiments.run_experiment.call_count == 1
        assert len(results) == 1

    def test_experiment_name_includes_dataset_name(
        self, experiments_dir: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.experiments.run_experiment.return_value = MagicMock()
        runner = _make_runner(experiments_dir, mock_phoenix_client)
        runner.run(names=["es_search"])
        call_kwargs = mock_phoenix_client.experiments.run_experiment.call_args.kwargs
        assert "es_search" in call_kwargs["experiment_name"]

    def test_async_task_is_wrapped_and_callable_by_sync_phoenix(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        """An async task must be transparently wrapped so Phoenix's sync runner
        can call it without getting back an unawaited coroutine."""
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "async_exp"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'async_result'\n")

        # Capture the task callable that is passed to run_experiment.
        captured: dict = {}

        def _capture_task(**kwargs: object) -> MagicMock:
            captured["task"] = kwargs["task"]
            return MagicMock()

        mock_phoenix_client.experiments.run_experiment.side_effect = _capture_task

        runner = _make_runner(base, mock_phoenix_client)
        runner.run()

        assert "task" in captured, "run_experiment was not called"
        wrapped = captured["task"]
        # The wrapped task must be a plain callable (not a coroutine function)
        # so Phoenix's sync runner can call it directly.
        import inspect

        assert not inspect.iscoroutinefunction(wrapped), (
            "Async task should have been wrapped into a sync callable"
        )
        # Calling it must return the real result, not a coroutine.
        result = wrapped(example=object())
        assert result == "async_result"

    def test_async_task_loop_is_reused_across_calls(
        self, tmp_path: Path, mock_phoenix_client: MagicMock
    ):
        """The per-thread event loop must stay open between successive task calls.
        Closing the loop after each call (e.g. asyncio.run()) breaks async I/O
        libraries that close transports after the coroutine returns."""
        base = tmp_path / "experiments"
        base.mkdir()
        exp = base / "loop_reuse_exp"
        exp.mkdir()
        (exp / "task.py").write_text("async def task(example): return 'ok'\n")

        captured: dict = {}

        def _capture_task(**kwargs: object) -> MagicMock:
            captured["task"] = kwargs["task"]
            return MagicMock()

        mock_phoenix_client.experiments.run_experiment.side_effect = _capture_task

        runner = _make_runner(base, mock_phoenix_client)
        runner.run()

        wrapped = captured["task"]
        # Simulate Phoenix calling the task for multiple examples sequentially.
        # If the loop were closed between calls the second call would raise
        # "RuntimeError: Event loop is closed".
        assert wrapped(example=object()) == "ok"
        assert wrapped(example=object()) == "ok"  # must not raise
