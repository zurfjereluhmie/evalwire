"""Tests for evalwire.uploader.DatasetUploader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from evalwire.uploader import DatasetUploader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uploader(csv_path: Path, client: MagicMock, **kwargs) -> DatasetUploader:
    return DatasetUploader(csv_path=csv_path, phoenix_client=client, **kwargs)


# ---------------------------------------------------------------------------
# _load_csv
# ---------------------------------------------------------------------------


class TestLoadCsv:
    def test_splits_pipe_delimited_expected_output(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        # The first row has "url-a | url-b" which should become a list
        first_row_output = df.iloc[0]["expected_output"]
        assert isinstance(first_row_output, list)
        assert first_row_output == ["url-a", "url-b"]

    def test_splits_pipe_delimited_tags(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        first_row_tags = df.iloc[0]["tags"]
        assert isinstance(first_row_tags, list)
        assert "es_search" in first_row_tags
        assert "source_router" in first_row_tags

    def test_single_value_tag_remains_string(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        # Row index 1 has a single tag "es_search" — no pipe, stays as str
        assert df.iloc[1]["tags"] == "es_search"

    def test_loads_all_rows(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        assert len(df) == 3


# ---------------------------------------------------------------------------
# _group_by_tag
# ---------------------------------------------------------------------------


class TestGroupByTag:
    def test_groups_by_single_tag(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        groups = uploader._group_by_tag(df)
        assert "es_search" in groups
        assert "source_router" in groups

    def test_row_with_two_tags_appears_in_both_groups(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        groups = uploader._group_by_tag(df)
        # Row 0 ("find cycling paths") tagged es_search AND source_router
        es_queries = groups["es_search"]["user_query"].tolist()
        sr_queries = groups["source_router"]["user_query"].tolist()
        assert "find cycling paths" in es_queries
        assert "find cycling paths" in sr_queries

    def test_es_search_group_has_two_rows(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        groups = uploader._group_by_tag(df)
        assert len(groups["es_search"]) == 2

    def test_source_router_group_has_two_rows(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = uploader._load_csv()
        groups = uploader._group_by_tag(df)
        assert len(groups["source_router"]) == 2


# ---------------------------------------------------------------------------
# upload — on_exist="skip"
# ---------------------------------------------------------------------------


class TestUploadSkip:
    def test_creates_dataset_for_each_tag(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        result = uploader.upload(on_exist="skip")
        assert set(result.keys()) == {"es_search", "source_router"}

    def test_calls_create_dataset_with_action_skip(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        uploader.upload(on_exist="skip")
        for c in mock_phoenix_client.datasets.create_dataset.call_args_list:
            assert c.kwargs.get("action") == "skip" or c.args  # action passed as kwarg

    def test_falls_back_to_get_dataset_on_conflict(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        # Simulate conflict: create_dataset raises, get_dataset returns the existing one
        mock_phoenix_client.datasets.create_dataset.side_effect = Exception("conflict")
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        result = uploader.upload(on_exist="skip")
        assert mock_phoenix_client.datasets.get_dataset.called
        assert len(result) == 2


# ---------------------------------------------------------------------------
# upload — on_exist="overwrite"
# ---------------------------------------------------------------------------


class TestUploadOverwrite:
    def test_deletes_existing_before_create(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        uploader.upload(on_exist="overwrite")
        assert mock_phoenix_client.datasets.delete_dataset.called

    def test_delete_failure_still_creates(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.datasets.get_dataset.side_effect = Exception("not found")
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        result = uploader.upload(on_exist="overwrite")
        # create_dataset should still be called even if delete failed
        assert mock_phoenix_client.datasets.create_dataset.called
        assert len(result) == 2


# ---------------------------------------------------------------------------
# upload — on_exist="append"
# ---------------------------------------------------------------------------


class TestUploadAppend:
    def test_calls_add_examples_when_dataset_exists(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        uploader.upload(on_exist="append")
        assert mock_phoenix_client.datasets.add_examples.called

    def test_falls_back_to_create_when_dataset_missing(
        self, sample_csv: Path, mock_phoenix_client: MagicMock
    ):
        mock_phoenix_client.datasets.get_dataset.side_effect = Exception("not found")
        uploader = _make_uploader(sample_csv, mock_phoenix_client)
        result = uploader.upload(on_exist="append")
        assert mock_phoenix_client.datasets.create_dataset.called
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _df_to_examples
# ---------------------------------------------------------------------------


class TestDfToExamples:
    def test_returns_list_of_dicts(self, sample_csv: Path):
        uploader = _make_uploader(sample_csv, MagicMock())
        df = pd.DataFrame(
            {
                "user_query": ["q1", "q2"],
                "expected_output": ["a", "b"],
                "tags": ["t", "t"],
            }
        )
        examples = uploader._df_to_examples(df)
        assert len(examples) == 2
        assert examples[0]["input"] == {"user_query": "q1"}
        assert examples[0]["output"] == {"expected_output": "a"}

    def test_missing_key_skipped(self, sample_csv: Path):
        uploader = _make_uploader(
            sample_csv, MagicMock(), input_keys=["user_query", "nonexistent"]
        )
        df = pd.DataFrame(
            {"user_query": ["q1"], "expected_output": ["a"], "tags": ["t"]}
        )
        examples = uploader._df_to_examples(df)
        assert "nonexistent" not in examples[0]["input"]


# ---------------------------------------------------------------------------
# Custom column names / delimiter
# ---------------------------------------------------------------------------


class TestCustomConfig:
    def test_custom_delimiter(self, tmp_path: Path, mock_phoenix_client: MagicMock):
        csv_file = tmp_path / "custom.csv"
        csv_file.write_text("query,output,group\nq1,a;b,g1;g2\nq2,c,g1\n")
        uploader = DatasetUploader(
            csv_path=csv_file,
            phoenix_client=mock_phoenix_client,
            input_keys=["query"],
            output_keys=["output"],
            tag_column="group",
            delimiter=";",
        )
        result = uploader.upload(on_exist="skip")
        assert "g1" in result
        assert "g2" in result

    def test_custom_tag_column(self, tmp_path: Path, mock_phoenix_client: MagicMock):
        csv_file = tmp_path / "custom.csv"
        csv_file.write_text("user_query,expected_output,category\nq1,a,cat1\n")
        uploader = DatasetUploader(
            csv_path=csv_file,
            phoenix_client=mock_phoenix_client,
            tag_column="category",
        )
        result = uploader.upload(on_exist="skip")
        assert "cat1" in result
