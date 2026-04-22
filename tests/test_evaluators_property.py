"""Property-based tests for evalwire evaluators using Hypothesis.

These tests verify invariants that must hold for *all* inputs, catching
edge cases that hand-crafted examples miss.
"""

from __future__ import annotations

import ast
import json
import math
import re

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from evalwire.evaluators.contains import make_contains_evaluator
from evalwire.evaluators.exact_match import make_exact_match_evaluator
from evalwire.evaluators.json_match import make_json_match_evaluator
from evalwire.evaluators.membership import make_membership_evaluator
from evalwire.evaluators.numeric_tolerance import make_numeric_tolerance_evaluator
from evalwire.evaluators.regex import make_regex_evaluator
from evalwire.evaluators.top_k import make_top_k_evaluator


def _expected_dict(value: str | list[str]) -> dict:
    """Wrap a value into the ``{"expected_output": ...}`` format."""
    return {"expected_output": value}


def _survives_literal_eval(s: str) -> bool:
    """Return True if ``_parse_expected`` will keep *s* as a ``str`` element.

    ``_parse_expected`` runs ``ast.literal_eval`` on string values.  Strings
    that evaluate to non-string Python literals (e.g. ``"0"`` -> ``int(0)``)
    are silently converted, causing type mismatches in downstream evaluators.
    """
    try:
        return isinstance(ast.literal_eval(s), str)
    except (ValueError, SyntaxError):
        return True


# Finite floats only (no NaN, no inf) -- mirrors real-world data.
finite_floats = st.floats(allow_nan=False, allow_infinity=False)


class TestNumericToleranceProperties:
    @given(value=finite_floats)
    def test_exact_match_always_passes(self, value: float):
        """A value compared to itself should always pass with default tolerance."""
        evaluator = make_numeric_tolerance_evaluator()
        result = evaluator(str(value), _expected_dict(str(value)))
        assert result is True

    @given(value=finite_floats, atol=st.floats(min_value=0, max_value=1e10))
    def test_result_is_bool(self, value: float, atol: float):
        """Return type is always bool, never crashes."""
        assume(not math.isnan(atol))
        evaluator = make_numeric_tolerance_evaluator(atol=atol)
        result = evaluator(str(value), _expected_dict(str(value)))
        assert isinstance(result, bool)

    @given(
        value=finite_floats,
        delta=st.floats(min_value=0, max_value=1e-8),
    )
    def test_within_default_tolerance(self, value: float, delta: float):
        """Values within default atol (1e-6) of each other should pass."""
        assume(abs(delta) <= 1e-6)
        evaluator = make_numeric_tolerance_evaluator()
        result = evaluator(str(value + delta), _expected_dict(str(value)))
        assert result is True

    @given(output=st.text())
    def test_non_numeric_string_returns_false(self, output: str):
        """Non-numeric output should return False, not crash."""
        assume(not _is_numeric(output))
        evaluator = make_numeric_tolerance_evaluator()
        result = evaluator(output, _expected_dict("42.0"))
        assert result is False

    @given(
        a=finite_floats,
        b=finite_floats,
        atol=st.floats(min_value=0, max_value=1e10),
        rtol=st.floats(min_value=0, max_value=1.0),
    )
    def test_tolerance_formula_matches_definition(
        self, a: float, b: float, atol: float, rtol: float
    ):
        """Result matches the formula: |a - b| <= atol + rtol * |b|."""
        assume(not math.isnan(atol) and not math.isnan(rtol))
        evaluator = make_numeric_tolerance_evaluator(atol=atol, rtol=rtol)
        result = evaluator(str(a), _expected_dict(str(b)))
        expected = abs(a - b) <= atol + rtol * abs(b)
        assert result == expected


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


class TestTopKProperties:
    @given(
        output=st.lists(st.text(min_size=1), min_size=1, max_size=50),
        expected=st.lists(st.text(min_size=1), min_size=1, max_size=10),
        k=st.integers(min_value=1, max_value=100),
    )
    def test_score_in_unit_interval(
        self, output: list[str], expected: list[str], k: int
    ):
        """Score must always be in [0.0, 1.0]."""
        evaluator = make_top_k_evaluator(K=k)
        score = evaluator(output, _expected_dict(expected))
        assert 0.0 <= score <= 1.0

    @given(k=st.integers(min_value=1, max_value=100))
    def test_perfect_score_when_all_at_top(self, k: int):
        """If all expected items are at position 0, score should be 1.0."""
        items = ["item"]
        evaluator = make_top_k_evaluator(K=k)
        score = evaluator(items, _expected_dict(items))
        assert score == 1.0

    @given(
        expected=st.lists(st.text(min_size=1), min_size=1, max_size=5),
        k=st.integers(min_value=1, max_value=50),
    )
    def test_score_zero_when_nothing_matches(self, expected: list[str], k: int):
        """If output contains none of the expected items, score should be 0.0."""
        output = ["__no_match__" + str(i) for i in range(k)]
        assume(not any(item in output for item in expected))
        evaluator = make_top_k_evaluator(K=k)
        score = evaluator(output, _expected_dict(expected))
        assert score == 0.0

    @given(output=st.lists(st.text(), max_size=20))
    def test_none_output_returns_zero(self, output: list[str]):
        """None output should return 0.0."""
        evaluator = make_top_k_evaluator()
        score = evaluator(None, _expected_dict(["anything"]))  # ty: ignore[invalid-argument-type]
        assert score == 0.0


class TestJsonMatchProperties:
    @given(data=st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
    def test_score_in_unit_interval(self, data: dict):
        """Score must always be in [0.0, 1.0]."""
        json_str = json.dumps(data)
        evaluator = make_json_match_evaluator()
        score = evaluator(json_str, _expected_dict(json_str))
        assert 0.0 <= score <= 1.0

    @given(data=st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
    def test_identical_json_scores_one(self, data: dict):
        """Identical JSON objects should score 1.0."""
        # Include a boolean so the JSON contains ``true`` which is not a valid
        # Python literal, preventing ``ast.literal_eval`` from converting the
        # expected string into a dict inside ``_parse_expected``.
        data = {**data, "__sentinel__": True}
        json_str = json.dumps(data)
        evaluator = make_json_match_evaluator()
        score = evaluator(json_str, _expected_dict(json_str))
        assert score == 1.0

    @given(output=st.text())
    def test_invalid_json_returns_zero(self, output: str):
        """Invalid JSON output should return 0.0, not crash."""
        assume(not _is_valid_json_object(output))
        evaluator = make_json_match_evaluator()
        score = evaluator(output, _expected_dict('{"key": "val"}'))
        assert score == 0.0


def _is_valid_json_object(s: str) -> bool:
    try:
        obj = json.loads(s)
        return isinstance(obj, dict)
    except (json.JSONDecodeError, TypeError):
        return False


class TestRegexProperties:
    @given(output=st.text())
    @settings(max_examples=200)
    def test_never_crashes_on_arbitrary_output(self, output: str):
        """Evaluator should not crash on any output string."""
        evaluator = make_regex_evaluator()
        result = evaluator(output, _expected_dict(r"\d+"))
        assert isinstance(result, bool)

    @given(literal=st.text(min_size=1, max_size=20))
    def test_literal_pattern_matches_itself(self, literal: str):
        """A regex-escaped literal should always match itself."""
        pattern = re.escape(literal)
        assume(_survives_literal_eval(pattern))
        evaluator = make_regex_evaluator()
        result = evaluator(literal, _expected_dict(pattern))
        assert result is True

    @given(output=st.text())
    def test_none_output_returns_false(self, output: str):
        """None output always returns False."""
        evaluator = make_regex_evaluator()
        result = evaluator(None, _expected_dict(r".*"))  # ty: ignore[invalid-argument-type]
        assert result is False


class TestExactMatchProperties:
    @given(value=st.text())
    def test_identity(self, value: str):
        """A string always exactly matches itself."""
        assume(_survives_literal_eval(value))
        evaluator = make_exact_match_evaluator()
        assert evaluator(value, _expected_dict(value)) is True

    @given(a=st.text(min_size=1), b=st.text(min_size=1))
    def test_different_strings_do_not_match(self, a: str, b: str):
        """Different strings should not match."""
        assume(a != b)
        evaluator = make_exact_match_evaluator()
        assert evaluator(a, _expected_dict(b)) is False


class TestContainsProperties:
    @given(haystack=st.text(min_size=1), needle=st.text(min_size=1))
    def test_substring_detected(self, haystack: str, needle: str):
        """If needle is a substring of haystack, evaluator returns True."""
        assume(_survives_literal_eval(needle))
        full = haystack + needle + haystack
        evaluator = make_contains_evaluator()
        assert evaluator(full, _expected_dict(needle)) is True

    @given(output=st.text())
    def test_none_output_returns_false(self, output: str):
        """None output always returns False."""
        evaluator = make_contains_evaluator()
        assert evaluator(None, _expected_dict("x")) is False  # ty: ignore[invalid-argument-type]


class TestMembershipProperties:
    @given(items=st.lists(st.text(min_size=1), min_size=1, max_size=10))
    def test_member_is_found(self, items: list[str]):
        """The first item should always be found in the expected set."""
        evaluator = make_membership_evaluator()
        assert evaluator(items[0], _expected_dict(items)) is True

    @given(
        items=st.lists(st.text(min_size=1), min_size=1, max_size=10),
        output=st.text(min_size=1),
    )
    def test_non_member_not_found(self, items: list[str], output: str):
        """A string not in the expected set should not be found."""
        assume(output not in items)
        evaluator = make_membership_evaluator()
        assert evaluator(output, _expected_dict(items)) is False
