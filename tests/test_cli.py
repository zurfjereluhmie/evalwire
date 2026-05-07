"""Tests for evalwire.cli — Click commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from evalwire.cli import main


def _runner() -> CliRunner:
    return CliRunner()


def _mock_client() -> MagicMock:
    client = MagicMock()
    ds = MagicMock()
    ds.id = "ds-1"
    client.datasets.create_dataset.return_value = ds
    client.datasets.get_dataset.return_value = ds
    client.datasets.add_examples_to_dataset.return_value = ds
    return client


class TestUploadCommand:
    def test_missing_csv_exits_with_usage_error(self):
        result = _runner().invoke(main, ["upload"])
        assert result.exit_code != 0
        assert "No CSV path provided" in result.output

    def test_upload_with_csv_flag_succeeds(self, sample_csv: Path):
        client = _mock_client()
        # skip path: get_dataset succeeds → no upload needed, just returns existing
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["upload", "--csv", str(sample_csv)])
        assert result.exit_code == 0
        assert "Uploaded" in result.output

    def test_upload_reports_correct_dataset_count(self, sample_csv: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["upload", "--csv", str(sample_csv)])
        assert "2 dataset(s)" in result.output

    def test_upload_on_exist_flag_passed_through(self, sample_csv: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                ["upload", "--csv", str(sample_csv), "--on-exist", "overwrite"],
            )
        assert result.exit_code == 0

    def test_upload_reads_csv_from_config_file(self, sample_csv: Path, tmp_path: Path):
        toml = tmp_path / "evalwire.toml"
        toml.write_text(f'[dataset]\ncsv_path = "{sample_csv}"\n')
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["upload", "--config", str(toml)])
        assert result.exit_code == 0

    def test_upload_cli_csv_overrides_config(self, sample_csv: Path, tmp_path: Path):
        # Config points to a nonexistent file; CLI --csv should win
        toml = tmp_path / "evalwire.toml"
        toml.write_text('[dataset]\ncsv_path = "nonexistent.csv"\n')
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                ["upload", "--csv", str(sample_csv), "--config", str(toml)],
            )
        assert result.exit_code == 0

    def test_upload_custom_input_output_keys(self, tmp_path: Path):
        csv_file = tmp_path / "custom.csv"
        csv_file.write_text("q,ans,grp\nq1,a1,g1\n")
        client = _mock_client()
        client.datasets.get_dataset.side_effect = ValueError("not found")
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "upload",
                    "--csv",
                    str(csv_file),
                    "--input-keys",
                    "q",
                    "--output-keys",
                    "ans",
                    "--tag-column",
                    "grp",
                ],
            )
        assert result.exit_code == 0

    def test_upload_exits_2_on_unexpected_error(self, sample_csv: Path):
        client = _mock_client()
        # Both get_dataset (skip check) and create_dataset raise
        client.datasets.get_dataset.side_effect = RuntimeError("also bad")
        client.datasets.create_dataset.side_effect = RuntimeError("unexpected")
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["upload", "--csv", str(sample_csv)])
        assert result.exit_code == 2


class TestRunCommand:
    def test_run_all_experiments(self, experiments_dir: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main, ["run", "--experiments", str(experiments_dir)]
            )
        assert result.exit_code == 0
        assert "2 experiment(s)" in result.output

    def test_run_single_named_experiment(self, experiments_dir: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "run",
                    "--experiments",
                    str(experiments_dir),
                    "--name",
                    "es_search",
                ],
            )
        assert result.exit_code == 0
        assert client.experiments.run_experiment.call_count == 1

    def test_run_dry_run_flag(self, experiments_dir: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                ["run", "--experiments", str(experiments_dir), "--dry-run", "2"],
            )
        assert result.exit_code == 0
        for c in client.experiments.run_experiment.call_args_list:
            assert c.kwargs.get("dry_run") == 2

    def test_run_custom_prefix(self, experiments_dir: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "run",
                    "--experiments",
                    str(experiments_dir),
                    "--prefix",
                    "myci",
                ],
            )
        assert result.exit_code == 0
        for c in client.experiments.run_experiment.call_args_list:
            assert c.kwargs["experiment_name"].startswith("myci_")

    def test_run_reads_experiments_dir_from_config(
        self, experiments_dir: Path, tmp_path: Path
    ):
        toml = tmp_path / "evalwire.toml"
        toml.write_text(f'[experiments]\ndir = "{experiments_dir}"\n')
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["run", "--config", str(toml)])
        assert result.exit_code == 0

    def test_run_exits_1_when_experiment_fails(self, experiments_dir: Path):
        client = _mock_client()
        client.experiments.run_experiment.side_effect = RuntimeError("boom")
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main, ["run", "--experiments", str(experiments_dir)]
            )
        assert result.exit_code == 1

    def test_run_exits_1_when_dataset_missing(self, experiments_dir: Path):
        client = _mock_client()
        client.datasets.get_dataset.side_effect = Exception("no dataset")
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main, ["run", "--experiments", str(experiments_dir)]
            )
        assert result.exit_code == 1

    def test_run_concurrency_option(self, experiments_dir: Path):
        client = _mock_client()
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "run",
                    "--experiments",
                    str(experiments_dir),
                    "--concurrency",
                    "4",
                ],
            )
        assert result.exit_code == 0

    def test_help_text_available(self):
        result = _runner().invoke(main, ["--help"])
        assert result.exit_code == 0
        result_upload = _runner().invoke(main, ["upload", "--help"])
        assert result_upload.exit_code == 0
        result_run = _runner().invoke(main, ["run", "--help"])
        assert result_run.exit_code == 0


def _make_ran_experiment(experiment_id="exp-1", scores=None):
    """Return a mock RanExperiment-like dict."""
    task_run = MagicMock()
    task_run.id = "run-1"
    task_run.output = "answer"
    task_run.error = None

    eval_runs = []
    for name, score in (scores or {}).items():
        ev = MagicMock()
        ev.experiment_run_id = "run-1"
        ev.name = name
        ev.result = MagicMock()
        ev.result.get = lambda k, default=None, _s=score: {"score": _s}.get(k, default)
        ev.error = None
        eval_runs.append(ev)

    return {
        "experiment_id": experiment_id,
        "task_runs": [task_run],
        "evaluation_runs": eval_runs,
        "dataset_id": "ds-1",
        "dataset_version_id": "dv-1",
        "experiment_metadata": {},
        "project_name": None,
    }


class TestExportCommand:
    def test_export_csv_exits_zero(self, tmp_path: Path):
        ran = _make_ran_experiment(scores={"accuracy": 0.9})
        client = _mock_client()
        client.experiments.get_experiment.return_value = ran
        out = tmp_path / "out.csv"
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "export",
                    "--experiment",
                    "exp-1",
                    "--format",
                    "csv",
                    "--output",
                    str(out),
                ],
            )
        assert result.exit_code == 0
        assert out.exists()

    def test_export_json_exits_zero(self, tmp_path: Path):
        ran = _make_ran_experiment(scores={"accuracy": 0.9})
        client = _mock_client()
        client.experiments.get_experiment.return_value = ran
        out = tmp_path / "out.json"
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                [
                    "export",
                    "--experiment",
                    "exp-1",
                    "--format",
                    "json",
                    "--output",
                    str(out),
                ],
            )
        assert result.exit_code == 0
        assert out.exists()

    def test_export_missing_experiment_flag_exits_nonzero(self):
        result = _runner().invoke(main, ["export"])
        assert result.exit_code != 0

    def test_export_not_found_experiment_exits_nonzero(self, tmp_path: Path):
        client = _mock_client()
        client.experiments.get_experiment.side_effect = ValueError("not found")
        out = tmp_path / "out.csv"
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(
                main,
                ["export", "--experiment", "missing", "--output", str(out)],
            )
        assert result.exit_code != 0


class TestCompareCommand:
    def test_compare_exits_zero(self):
        ran_a = _make_ran_experiment("exp-a", scores={"accuracy": 0.8})
        ran_b = _make_ran_experiment("exp-b", scores={"accuracy": 0.9})
        client = _mock_client()
        client.experiments.get_experiment.side_effect = lambda experiment_id: (
            ran_a if experiment_id == "exp-a" else ran_b
        )
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["compare", "exp-a", "exp-b"])
        assert result.exit_code == 0
        assert "accuracy" in result.output

    def test_compare_shows_delta(self):
        ran_a = _make_ran_experiment("exp-a", scores={"accuracy": 0.8})
        ran_b = _make_ran_experiment("exp-b", scores={"accuracy": 0.9})
        client = _mock_client()
        client.experiments.get_experiment.side_effect = lambda experiment_id: (
            ran_a if experiment_id == "exp-a" else ran_b
        )
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["compare", "exp-a", "exp-b"])
        assert (
            "0.10" in result.output
            or "+0.1" in result.output
            or "delta" in result.output.lower()
        )

    def test_compare_missing_args_exits_nonzero(self):
        result = _runner().invoke(main, ["compare"])
        assert result.exit_code != 0


class TestReportCommand:
    def test_report_exits_zero(self):
        ran = _make_ran_experiment(scores={"accuracy": 0.75})
        client = _mock_client()
        client.experiments.get_experiment.return_value = ran
        with patch("evalwire.cli._make_client", return_value=client):
            result = _runner().invoke(main, ["report", "--experiment", "exp-1"])
        assert result.exit_code == 0
        assert "accuracy" in result.output

    def test_report_missing_experiment_flag_exits_nonzero(self):
        result = _runner().invoke(main, ["report"])
        assert result.exit_code != 0
