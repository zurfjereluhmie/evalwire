"""Tests for evalwire.config — TOML config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from evalwire.config import (
    get_dataset_config,
    get_experiments_config,
    get_phoenix_config,
    load_config,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FULL_TOML = """\
[dataset]
csv_path      = "data/testset.csv"
input_keys    = ["user_query"]
output_keys   = ["expected_output"]
tag_column    = "tags"
delimiter     = "|"
on_exist      = "skip"

[experiments]
dir           = "experiments"
concurrency   = 2
prefix        = "ci"

[phoenix]
base_url      = "http://localhost:6006"
"""


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_returns_empty_dict_when_file_absent(self, tmp_path: Path):
        result = load_config(tmp_path / "nonexistent.toml")
        assert result == {}

    def test_loads_full_config(self, tmp_path: Path):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text(FULL_TOML)
        result = load_config(cfg_file)
        assert result["dataset"]["csv_path"] == "data/testset.csv"
        assert result["experiments"]["concurrency"] == 2
        assert result["phoenix"]["base_url"] == "http://localhost:6006"

    def test_accepts_path_object(self, tmp_path: Path):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text("[dataset]\ncsv_path = 'x.csv'\n")
        result = load_config(Path(cfg_file))
        assert result["dataset"]["csv_path"] == "x.csv"

    def test_accepts_string_path(self, tmp_path: Path):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text("[dataset]\ncsv_path = 'y.csv'\n")
        result = load_config(str(cfg_file))
        assert result["dataset"]["csv_path"] == "y.csv"

    def test_defaults_to_evalwire_toml_in_cwd(self, tmp_path: Path, monkeypatch):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text("[dataset]\ncsv_path = 'cwd.csv'\n")
        monkeypatch.chdir(tmp_path)
        result = load_config()  # no argument — should find ./evalwire.toml
        assert result["dataset"]["csv_path"] == "cwd.csv"

    def test_empty_toml_returns_empty_dict(self, tmp_path: Path):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text("")
        result = load_config(cfg_file)
        assert result == {}

    def test_invalid_toml_raises(self, tmp_path: Path):
        cfg_file = tmp_path / "evalwire.toml"
        cfg_file.write_text("this is not valid toml ][[\n")
        with pytest.raises(Exception):
            load_config(cfg_file)


# ---------------------------------------------------------------------------
# Section accessors
# ---------------------------------------------------------------------------


class TestSectionAccessors:
    def setup_method(self):
        self.config = {
            "dataset": {"csv_path": "data/x.csv"},
            "experiments": {"dir": "exps", "concurrency": 4},
            "phoenix": {"base_url": "http://ph:6006"},
        }

    def test_get_dataset_config(self):
        result = get_dataset_config(self.config)
        assert result == {"csv_path": "data/x.csv"}

    def test_get_experiments_config(self):
        result = get_experiments_config(self.config)
        assert result["concurrency"] == 4

    def test_get_phoenix_config(self):
        result = get_phoenix_config(self.config)
        assert result["base_url"] == "http://ph:6006"

    def test_get_dataset_config_missing_section(self):
        assert get_dataset_config({}) == {}

    def test_get_experiments_config_missing_section(self):
        assert get_experiments_config({}) == {}

    def test_get_phoenix_config_missing_section(self):
        assert get_phoenix_config({}) == {}
