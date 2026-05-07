"""Tests for evalwire.validator — DatasetValidator."""

import textwrap
from pathlib import Path

import pytest

from evalwire.validator import DatasetValidator, ValidationIssue, ValidationResult


@pytest.fixture()
def valid_csv(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        user_query,expected_output,tags
        "what is python","A language","es_search"
        "find cycling paths","url-a","es_search | source_router"
    """)
    f = tmp_path / "valid.csv"
    f.write_text(content)
    return f


@pytest.fixture()
def missing_tag_col_csv(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        user_query,expected_output
        "what is python","A language"
    """)
    f = tmp_path / "no_tags.csv"
    f.write_text(content)
    return f


@pytest.fixture()
def empty_tag_csv(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        user_query,expected_output,tags
        "what is python","A language",""
        "find paths","url","es_search"
    """)
    f = tmp_path / "empty_tag.csv"
    f.write_text(content)
    return f


@pytest.fixture()
def empty_expected_output_csv(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        user_query,expected_output,tags
        "what is python","","es_search"
        "find paths","url","es_search"
    """)
    f = tmp_path / "empty_output.csv"
    f.write_text(content)
    return f


@pytest.fixture()
def missing_input_col_csv(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        wrong_col,expected_output,tags
        "what is python","A language","es_search"
    """)
    f = tmp_path / "missing_input.csv"
    f.write_text(content)
    return f


class TestValidationResult:
    def test_is_valid_when_no_issues(self):
        result = ValidationResult(issues=[])
        assert result.is_valid is True

    def test_is_invalid_when_has_issues(self):
        result = ValidationResult(issues=[ValidationIssue(row=1, message="bad")])
        assert result.is_valid is False

    def test_repr_shows_issue_count(self):
        result = ValidationResult(issues=[ValidationIssue(row=1, message="bad")])
        assert "1" in repr(result)


class TestValidationIssue:
    def test_has_row_and_message(self):
        issue = ValidationIssue(row=3, message="empty tag")
        assert issue.row == 3
        assert issue.message == "empty tag"

    def test_row_none_for_structural_issues(self):
        issue = ValidationIssue(row=None, message="missing column: tags")
        assert issue.row is None


class TestDatasetValidator:
    def test_valid_csv_returns_no_issues(self, valid_csv: Path):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=valid_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert result.is_valid is True
        assert result.issues == []

    def test_missing_tag_column_is_an_issue(self, missing_tag_col_csv: Path):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=missing_tag_col_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert not result.is_valid
        messages = [i.message for i in result.issues]
        assert any("tags" in m for m in messages)

    def test_missing_input_column_is_an_issue(self, missing_input_col_csv: Path):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=missing_input_col_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert not result.is_valid
        messages = [i.message for i in result.issues]
        assert any("user_query" in m for m in messages)

    def test_empty_tag_reported_with_row_number(self, empty_tag_csv: Path):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=empty_tag_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert not result.is_valid
        rows_with_issues = [i.row for i in result.issues if i.row is not None]
        assert 1 in rows_with_issues

    def test_empty_expected_output_reported_with_row_number(
        self, empty_expected_output_csv: Path
    ):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=empty_expected_output_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert not result.is_valid
        rows_with_issues = [i.row for i in result.issues if i.row is not None]
        assert 1 in rows_with_issues

    def test_custom_tag_column_name(self, tmp_path: Path):
        f = tmp_path / "custom.csv"
        f.write_text("q,ans,group\nhi,hello,grp1\n")
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=f,
            input_keys=["q"],
            output_keys=["ans"],
            tag_column="group",
        )
        assert result.is_valid

    def test_nonexistent_file_raises(self, tmp_path: Path):
        validator = DatasetValidator()
        with pytest.raises(FileNotFoundError):
            validator.validate(
                csv_path=tmp_path / "nonexistent.csv",
                input_keys=["q"],
                output_keys=["ans"],
            )

    def test_multiple_issues_all_reported(self, tmp_path: Path):
        f = tmp_path / "bad.csv"
        f.write_text("wrong,also_wrong\nval,val\n")
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=f,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        assert len(result.issues) >= 3

    def test_structural_issues_have_no_row(self, missing_tag_col_csv: Path):
        validator = DatasetValidator()
        result = validator.validate(
            csv_path=missing_tag_col_csv,
            input_keys=["user_query"],
            output_keys=["expected_output"],
        )
        structural = [i for i in result.issues if i.row is None]
        assert len(structural) >= 1
