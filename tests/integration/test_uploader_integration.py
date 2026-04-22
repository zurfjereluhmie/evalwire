"""Integration tests for evalwire.uploader.DatasetUploader.

These tests run against a real in-memory Phoenix instance and verify the
full upload lifecycle: CSV parsing, dataset creation, skip/append modes,
and correct example counts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evalwire.uploader import DatasetUploader

pytestmark = pytest.mark.integration


class TestUploadLifecycle:
    """Upload -> fetch -> verify round-trip against a real Phoenix server."""

    def test_creates_one_dataset_per_tag(
        self, phoenix_client, integration_csv: tuple[Path, str, str]
    ):
        csv_path, search_tag, router_tag = integration_csv
        uploader = DatasetUploader(
            csv_path=csv_path,
            phoenix_client=phoenix_client,
        )
        results = uploader.upload(on_exist="skip")

        assert set(results.keys()) == {search_tag, router_tag}

    def test_created_datasets_have_correct_example_counts(
        self, phoenix_client, integration_csv: tuple[Path, str, str]
    ):
        csv_path, search_tag, router_tag = integration_csv
        uploader = DatasetUploader(
            csv_path=csv_path,
            phoenix_client=phoenix_client,
        )
        uploader.upload(on_exist="skip")

        search_ds = phoenix_client.datasets.get_dataset(dataset=search_tag)
        router_ds = phoenix_client.datasets.get_dataset(dataset=router_tag)
        # "search" has rows 0 and 1, "router" has rows 0 and 2
        assert len(search_ds) == 2
        assert len(router_ds) == 2

    def test_skip_does_not_duplicate(
        self, phoenix_client, integration_csv: tuple[Path, str, str]
    ):
        csv_path, search_tag, _router_tag = integration_csv
        uploader = DatasetUploader(
            csv_path=csv_path,
            phoenix_client=phoenix_client,
        )
        # First upload creates the datasets
        uploader.upload(on_exist="skip")

        # Second upload with skip should return the existing dataset
        results = uploader.upload(on_exist="skip")
        assert search_tag in results

        # Verify no extra examples were added
        search_ds = phoenix_client.datasets.get_dataset(dataset=search_tag)
        assert len(search_ds) == 2

    def test_append_adds_examples(
        self, phoenix_client, integration_csv: tuple[Path, str, str]
    ):
        csv_path, search_tag, _router_tag = integration_csv
        uploader = DatasetUploader(
            csv_path=csv_path,
            phoenix_client=phoenix_client,
        )
        uploader.upload(on_exist="skip")
        count_before = len(phoenix_client.datasets.get_dataset(dataset=search_tag))

        uploader.upload(on_exist="append")
        count_after = len(phoenix_client.datasets.get_dataset(dataset=search_tag))

        assert count_after == count_before + 2  # 2 more "search" rows

    def test_custom_keys(self, phoenix_client, tmp_path: Path):
        import uuid

        tag = f"grp_{uuid.uuid4().hex[:8]}"
        csv_file = tmp_path / "custom.csv"
        csv_file.write_text(f"question,answer,group\nq1,a1,{tag}\nq2,a2,{tag}\n")

        uploader = DatasetUploader(
            csv_path=csv_file,
            phoenix_client=phoenix_client,
            input_keys=["question"],
            output_keys=["answer"],
            tag_column="group",
        )
        results = uploader.upload(on_exist="skip")
        assert tag in results

        ds = phoenix_client.datasets.get_dataset(dataset=tag)
        assert len(ds) == 2
        # Verify the example structure has the right keys
        example = ds[0]
        assert "question" in example["input"]
        assert "answer" in example["output"]
