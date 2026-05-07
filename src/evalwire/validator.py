"""Testset validation for evalwire CSV uploads."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class ValidationIssue:
    """A single validation problem found in a testset."""

    row: int | None
    message: str


@dataclass
class ValidationResult:
    """Aggregated result of a validation run."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    def __repr__(self) -> str:
        return f"ValidationResult(issues={len(self.issues)})"


class DatasetValidator:
    """Validate a CSV testset before uploading to Phoenix.

    Checks performed:
    - Required columns (input keys, output keys, tag column) are present.
    - No row has an empty tag value.
    - No row has an empty expected output value.
    """

    def validate(
        self,
        csv_path: Path | str,
        input_keys: list[str],
        output_keys: list[str],
        tag_column: str = "tags",
    ) -> ValidationResult:
        """Validate *csv_path* against the given schema.

        Parameters
        ----------
        csv_path:
            Path to the CSV file to validate.
        input_keys:
            Expected input column names.
        output_keys:
            Expected output column names.
        tag_column:
            Name of the column used for dataset splitting.

        Returns
        -------
        ValidationResult
            Contains all discovered issues (structural and row-level).

        Raises
        ------
        FileNotFoundError
            If *csv_path* does not exist.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)
        issues: list[ValidationIssue] = []

        required_columns = list(input_keys) + list(output_keys) + [tag_column]
        for col in required_columns:
            if col not in df.columns:
                issues.append(
                    ValidationIssue(row=None, message=f"missing column: {col}")
                )

        missing_cols = {col for col in required_columns if col not in df.columns}

        if tag_column not in missing_cols:
            for idx, value in enumerate(df[tag_column], start=1):
                if pd.isna(value) or str(value).strip() == "":
                    issues.append(
                        ValidationIssue(
                            row=idx, message=f"empty tag in column '{tag_column}'"
                        )
                    )

        for output_key in output_keys:
            if output_key in missing_cols:
                continue
            for idx, value in enumerate(df[output_key], start=1):
                if pd.isna(value) or str(value).strip() == "":
                    issues.append(
                        ValidationIssue(
                            row=idx,
                            message=f"empty expected output in column '{output_key}'",
                        )
                    )

        return ValidationResult(issues=issues)
