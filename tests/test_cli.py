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
