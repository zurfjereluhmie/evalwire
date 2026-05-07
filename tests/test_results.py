"""Tests for evalwire.results — ResultCollector."""

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from evalwire.results import ResultCollector


def _make_eval_run(name: str, score: float | None, run_id: str = "run-1"):
    ev = MagicMock()
    ev.experiment_run_id = run_id
    ev.name = name
    ev.result = MagicMock()
    ev.result.get = lambda k, default=None: {"score": score}.get(k, default)
    ev.error = None
    return ev


def _make_task_run(run_id: str = "run-1", output: str = "answer"):
    run = MagicMock()
    run.id = run_id
    run.output = output
    run.error = None
    return run


def _make_experiment(
    experiment_id: str = "exp-1",
    task_runs=None,
    evaluation_runs=None,
):
    exp = MagicMock()
    exp.__getitem__ = lambda self, k: {
        "experiment_id": experiment_id,
        "task_runs": task_runs or [],
        "evaluation_runs": evaluation_runs or [],
    }[k]
    exp.get = lambda k, default=None: {
        "experiment_id": experiment_id,
        "task_runs": task_runs or [],
        "evaluation_runs": evaluation_runs or [],
    }.get(k, default)
    return exp


def _make_ran_experiment(
    experiment_id: str = "exp-1",
    task_runs=None,
    evaluation_runs=None,
):
    exp = {
        "experiment_id": experiment_id,
        "task_runs": task_runs or [],
        "evaluation_runs": evaluation_runs or [],
        "dataset_id": "ds-1",
        "dataset_version_id": "dv-1",
        "experiment_metadata": {},
        "project_name": None,
    }
    return exp


def _mock_client(ran_experiment=None):
    client = MagicMock()
    client.experiments.get_experiment.return_value = (
        ran_experiment or _make_ran_experiment()
    )
    return client


class TestResultCollectorGet:
    def test_get_calls_get_experiment_with_id(self):
        client = _mock_client()
        rc = ResultCollector(client)
        rc.get("exp-1")
        client.experiments.get_experiment.assert_called_once_with(experiment_id="exp-1")

    def test_get_returns_ran_experiment(self):
        ran = _make_ran_experiment("exp-42")
        client = _mock_client(ran)
        rc = ResultCollector(client)
        result = rc.get("exp-42")
        assert result["experiment_id"] == "exp-42"

    def test_get_raises_when_not_found(self):
        client = _mock_client()
        client.experiments.get_experiment.side_effect = ValueError("not found")
        rc = ResultCollector(client)
        with pytest.raises(ValueError, match="not found"):
            rc.get("missing-id")


class TestResultCollectorExport:
    def _build_rc_with_data(self):
        task_run = _make_task_run("run-1", "42")
        eval_run = _make_eval_run("accuracy", 0.9, "run-1")
        ran = _make_ran_experiment(
            "exp-1",
            task_runs=[task_run],
            evaluation_runs=[eval_run],
        )
        client = _mock_client(ran)
        return ResultCollector(client)

    def test_export_csv_creates_file(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        out = tmp_path / "results.csv"
        rc.export("exp-1", format="csv", path=out)
        assert out.exists()

    def test_export_csv_has_header_row(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        out = tmp_path / "results.csv"
        rc.export("exp-1", format="csv", path=out)
        with open(out) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
        assert "run_id" in headers
        assert "output" in headers

    def test_export_csv_has_data_rows(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        out = tmp_path / "results.csv"
        rc.export("exp-1", format="csv", path=out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["run_id"] == "run-1"

    def test_export_json_creates_valid_json(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        out = tmp_path / "results.json"
        rc.export("exp-1", format="json", path=out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_export_json_row_has_expected_keys(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        out = tmp_path / "results.json"
        rc.export("exp-1", format="json", path=out)
        data = json.loads(out.read_text())
        assert "run_id" in data[0]
        assert "output" in data[0]

    def test_export_unsupported_format_raises(self, tmp_path: Path):
        rc = self._build_rc_with_data()
        with pytest.raises(ValueError, match="format"):
            rc.export("exp-1", format="parquet", path=tmp_path / "x")


class TestResultCollectorCompare:
    def _build_rc(self, score_a: float, score_b: float):
        task_run_a = _make_task_run("run-a", "out-a")
        eval_run_a = _make_eval_run("accuracy", score_a, "run-a")
        ran_a = _make_ran_experiment("exp-a", [task_run_a], [eval_run_a])

        task_run_b = _make_task_run("run-b", "out-b")
        eval_run_b = _make_eval_run("accuracy", score_b, "run-b")
        ran_b = _make_ran_experiment("exp-b", [task_run_b], [eval_run_b])

        client = MagicMock()
        client.experiments.get_experiment.side_effect = lambda experiment_id: (
            ran_a if experiment_id == "exp-a" else ran_b
        )
        return ResultCollector(client)

    def test_compare_returns_dict_with_evaluator_names(self):
        rc = self._build_rc(0.8, 0.9)
        result = rc.compare("exp-a", "exp-b")
        assert "accuracy" in result

    def test_compare_delta_is_b_minus_a(self):
        rc = self._build_rc(0.8, 0.9)
        result = rc.compare("exp-a", "exp-b")
        assert result["accuracy"]["delta"] == pytest.approx(0.1)

    def test_compare_includes_scores_for_both(self):
        rc = self._build_rc(0.6, 0.8)
        result = rc.compare("exp-a", "exp-b")
        assert result["accuracy"]["score_a"] == pytest.approx(0.6)
        assert result["accuracy"]["score_b"] == pytest.approx(0.8)


class TestResultCollectorReport:
    def test_report_returns_string(self):
        task_run = _make_task_run("run-1", "42")
        eval_run = _make_eval_run("accuracy", 0.75, "run-1")
        ran = _make_ran_experiment("exp-1", [task_run], [eval_run])
        client = _mock_client(ran)
        rc = ResultCollector(client)
        report = rc.report("exp-1")
        assert isinstance(report, str)

    def test_report_contains_experiment_id(self):
        ran = _make_ran_experiment("exp-99")
        client = _mock_client(ran)
        rc = ResultCollector(client)
        report = rc.report("exp-99")
        assert "exp-99" in report

    def test_report_contains_evaluator_scores(self):
        task_run = _make_task_run("run-1", "42")
        eval_run = _make_eval_run("accuracy", 0.75, "run-1")
        ran = _make_ran_experiment("exp-1", [task_run], [eval_run])
        client = _mock_client(ran)
        rc = ResultCollector(client)
        report = rc.report("exp-1")
        assert "accuracy" in report
        assert "0.75" in report

    def test_report_is_markdown(self):
        ran = _make_ran_experiment("exp-1")
        client = _mock_client(ran)
        rc = ResultCollector(client)
        report = rc.report("exp-1")
        assert "#" in report
