"""DatasetUploader — uploads a CSV testset to Arize Phoenix as named datasets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

logger = logging.getLogger(__name__)


class DatasetUploader:
    """Upload a human-curated CSV testset to Arize Phoenix.

    Each unique value found in ``tag_column`` becomes a separate Phoenix
    dataset. A row tagged with multiple pipe-delimited values is added to
    each corresponding dataset.

    Parameters
    ----------
    csv_path:
        Path to the CSV file.
    phoenix_client:
        An initialised ``phoenix.client.Client`` instance.
    input_keys:
        Column names that form the ``input`` of each dataset example.
    output_keys:
        Column names that form the ``output`` of each dataset example.
    tag_column:
        Column used to split rows into separate datasets.
    delimiter:
        Delimiter used to split multi-value cells (tags and output columns).
    """

    def __init__(
        self,
        csv_path: Path | str,
        phoenix_client: Any,
        input_keys: list[str] | None = None,
        output_keys: list[str] | None = None,
        tag_column: str = "tags",
        delimiter: str = "|",
    ) -> None:
        self.csv_path = Path(csv_path)
        self.client = phoenix_client
        self.input_keys = list(input_keys) if input_keys is not None else ["user_query"]
        self.output_keys = (
            list(output_keys) if output_keys is not None else ["expected_output"]
        )
        self.tag_column = tag_column
        self.delimiter = delimiter

    def upload(
        self,
        on_exist: Literal["skip", "overwrite", "append"] = "skip",
    ) -> dict[str, Any]:
        """Upload one Phoenix dataset per unique tag value found in the CSV.

        Parameters
        ----------
        on_exist:
            How to handle a dataset that already exists in Phoenix:
            - ``"skip"``      — leave the existing dataset untouched (default).
            - ``"overwrite"`` — delete and re-create.
            - ``"append"``    — add new examples to the existing dataset.

        Returns
        -------
        dict[str, Any]
            Mapping of tag name → created/updated dataset object.
        """
        df = self._load_csv()
        groups = self._group_by_tag(df)
        results: dict[str, Any] = {}

        for tag, group_df in groups.items():
            logger.info("Uploading dataset %r (%d rows)…", tag, len(group_df))
            dataset = self._upload_one(tag, group_df, on_exist)
            results[tag] = dataset

        return results

    def _load_csv(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)
        # Split any column whose values contain the delimiter character.
        # Use pd.api.types.is_string_dtype to support both object (pandas <3)
        # and the new StringDtype (pandas >=3).
        delimiter = self.delimiter
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                mask = (
                    df[col].astype(str).str.contains(delimiter, regex=False, na=False)
                )
                if mask.any() or col == self.tag_column:
                    df[col] = (
                        df[col]
                        .astype(str)
                        .apply(
                            lambda v, d=delimiter: (
                                [s.strip() for s in v.split(d)] if d in v else v
                            )
                        )
                    )
        return df

    def _group_by_tag(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Return one DataFrame per unique tag value."""
        groups: dict[str, list[int]] = {}
        for idx, row in df.iterrows():
            tags_cell = row[self.tag_column]
            tags: list[str] = (
                tags_cell if isinstance(tags_cell, list) else [str(tags_cell)]
            )
            for tag in tags:
                tag = tag.strip()
                if tag:
                    groups.setdefault(tag, []).append(cast(int, idx))

        return {
            tag: df.loc[indices].reset_index(drop=True)
            for tag, indices in groups.items()
        }

    def _upload_one(
        self,
        name: str,
        df: pd.DataFrame,
        on_exist: Literal["skip", "overwrite", "append"],
    ) -> Any:
        if on_exist == "skip":
            try:
                existing = self.client.datasets.get_dataset(name=name)
                logger.info("Dataset %r already exists, skipping.", name)
                return existing
            except Exception:
                pass  # does not exist yet — fall through to create
            return self.client.datasets.create_dataset(
                dataframe=df,
                name=name,
                input_keys=self.input_keys,
                output_keys=self.output_keys,
            )

        elif on_exist == "overwrite":
            try:
                existing = self.client.datasets.get_dataset(name=name)
                self.client.datasets.delete_dataset(id=existing.id)
                logger.debug("Deleted existing dataset %r for overwrite.", name)
            except Exception:
                pass  # does not exist — nothing to delete
            return self.client.datasets.create_dataset(
                dataframe=df,
                name=name,
                input_keys=self.input_keys,
                output_keys=self.output_keys,
            )

        else:  # "append"
            try:
                existing = self.client.datasets.get_dataset(name=name)
                dataset = self.client.datasets.add_examples(
                    dataset_id=existing.id,
                    dataframe=df,
                    input_keys=self.input_keys,
                    output_keys=self.output_keys,
                )
                logger.debug("Appended %d examples to dataset %r.", len(df), name)
                return dataset
            except Exception:
                logger.debug(
                    "Dataset %r not found for append; creating it instead.", name
                )
            return self.client.datasets.create_dataset(
                dataframe=df,
                name=name,
                input_keys=self.input_keys,
                output_keys=self.output_keys,
            )
