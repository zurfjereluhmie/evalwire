"""Tests for evalwire.evaluators."""

import json
import re
import sys
from unittest.mock import MagicMock

import pytest

from evalwire.evaluators import (
    make_contains_evaluator,
    make_exact_match_evaluator,
    make_json_match_evaluator,
    make_llm_judge_evaluator,
    make_membership_evaluator,
    make_numeric_tolerance_evaluator,
    make_regex_evaluator,
    make_schema_evaluator,
    make_top_k_evaluator,
)


class TestMakeTopKEvaluator:
    def test_returns_callable_named_top_k(self):
        fn = make_top_k_evaluator(K=10)
        assert callable(fn)
        assert fn.__name__ == "top_k"  # ty: ignore[unresolved-attribute]

    def test_item_at_rank_1_scores_1(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["url-a"], {"expected_output": ["url-a"]})
        assert score == pytest.approx(1.0)

    def test_item_not_found_scores_0(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["url-x", "url-y"], {"expected_output": ["url-z"]})
        assert score == pytest.approx(0.0)

    def test_item_beyond_k_scores_0(self):
        top_k = make_top_k_evaluator(K=2)
        # url-c is at index 2, which is >= K=2 so outside the window
        score = top_k(["url-a", "url-b", "url-c"], {"expected_output": ["url-c"]})
        assert score == pytest.approx(0.0)

    def test_position_weighting(self):
        # K=10, item at position 5 → score = 1 - 5/10 = 0.5
        top_k = make_top_k_evaluator(K=10)
        output = ["a", "b", "c", "d", "e", "target"]
        score = top_k(output, {"expected_output": ["target"]})
        assert score == pytest.approx(0.5)

    def test_multiple_expected_items_averaged(self):
        # K=10: "a" at pos 0 → 1.0; "b" at pos 1 → 0.9; mean = 0.95
        top_k = make_top_k_evaluator(K=10)
        output = ["a", "b", "c"]
        score = top_k(output, {"expected_output": ["a", "b"]})
        assert score == pytest.approx(0.95)

    def test_partial_hit_among_multiple(self):
        # K=4: "a" at pos 0 → 1.0; "missing" not found → 0.0; mean = 0.5
        top_k = make_top_k_evaluator(K=4)
        output = ["a", "b", "c", "d"]
        score = top_k(output, {"expected_output": ["a", "missing"]})
        assert score == pytest.approx(0.5)

    def test_empty_expected_returns_0(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["a", "b"], {"expected_output": []})
        assert score == pytest.approx(0.0)

    def test_expected_as_string_literal_eval(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["url-a"], {"expected_output": "['url-a']"})
        assert score == pytest.approx(1.0)

    def test_default_k_is_20(self):
        top_k = make_top_k_evaluator()
        # item at position 19 (last in top-20) → 1 - 19/20 = 0.05
        output = [str(i) for i in range(20)]
        score = top_k(output, {"expected_output": ["19"]})
        assert score == pytest.approx(1 - 19 / 20)

    def test_score_at_last_k_position(self):
        # K=5, item at position 4 → 1 - 4/5 = 0.2
        top_k = make_top_k_evaluator(K=5)
        output = ["a", "b", "c", "d", "target"]
        score = top_k(output, {"expected_output": ["target"]})
        assert score == pytest.approx(0.2)

    def test_empty_output_scores_0(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k([], {"expected_output": ["url-a"]})
        assert score == pytest.approx(0.0)

    def test_missing_expected_output_key_returns_0(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["a"], {})
        assert score == pytest.approx(0.0)

    def test_bare_string_expected_output_is_treated_as_single_item(self):
        """A plain identifier string (e.g. from a CSV column) must not crash
        ast.literal_eval and should be treated as a single-item expected list."""
        top_k = make_top_k_evaluator(K=10)
        # "some_url" is a bare identifier — not a Python literal
        score = top_k(["some_url"], {"expected_output": "some_url"})
        assert score == pytest.approx(1.0)

    def test_bare_string_expected_output_no_match(self):
        top_k = make_top_k_evaluator(K=10)
        score = top_k(["other_url"], {"expected_output": "some_url"})
        assert score == pytest.approx(0.0)


class TestMakeMembershipEvaluator:
    def test_returns_callable_named_is_in(self):
        fn = make_membership_evaluator()
        assert callable(fn)
        assert fn.__name__ == "is_in"  # ty: ignore[unresolved-attribute]

    def test_match_returns_true(self):
        is_in = make_membership_evaluator()
        assert (
            is_in("es_search", {"expected_output": ["es_search", "web_search"]}) is True
        )

    def test_no_match_returns_false(self):
        is_in = make_membership_evaluator()
        assert (
            is_in("unknown", {"expected_output": ["es_search", "web_search"]}) is False
        )

    def test_expected_as_string_literal_eval(self):
        is_in = make_membership_evaluator()
        assert is_in("es_search", {"expected_output": "['es_search']"}) is True

    def test_empty_expected_returns_false(self):
        is_in = make_membership_evaluator()
        assert is_in("es_search", {"expected_output": []}) is False

    def test_missing_expected_output_key_returns_false(self):
        is_in = make_membership_evaluator()
        assert is_in("es_search", {}) is False

    def test_single_item_list_match(self):
        is_in = make_membership_evaluator()
        assert is_in("only", {"expected_output": ["only"]}) is True

    def test_case_sensitive(self):
        is_in = make_membership_evaluator()
        assert is_in("ES_SEARCH", {"expected_output": ["es_search"]}) is False

    def test_bare_string_expected_output_is_treated_as_single_item(self):
        """A plain identifier string (e.g. from a CSV column) must not crash
        ast.literal_eval and should be treated as a single-item expected list."""
        is_in = make_membership_evaluator()
        # "elasticsearch" is a bare identifier — not a Python literal
        assert is_in("elasticsearch", {"expected_output": "elasticsearch"}) is True

    def test_bare_string_expected_output_no_match(self):
        is_in = make_membership_evaluator()
        assert is_in("cms", {"expected_output": "elasticsearch"}) is False


class TestMakeExactMatchEvaluator:
    def test_returns_callable_named_exact_match(self):
        fn = make_exact_match_evaluator()
        assert callable(fn)
        assert fn.__name__ == "exact_match"  # ty: ignore[unresolved-attribute]

    def test_exact_hit_returns_true(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("hello world", {"expected_output": ["hello world"]}) is True

    def test_exact_hit_bare_string_expected(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("hello world", {"expected_output": "hello world"}) is True

    def test_different_string_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("hello world", {"expected_output": ["Hello World"]}) is False

    def test_case_mismatch_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("Python", {"expected_output": ["python"]}) is False

    def test_extra_whitespace_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match(" hello", {"expected_output": ["hello"]}) is False

    def test_empty_expected_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("hello", {"expected_output": []}) is False

    def test_missing_key_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("hello", {}) is False

    def test_none_output_returns_false(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match(None, {"expected_output": ["hello"]}) is False  # ty: ignore[invalid-argument-type]

    def test_empty_string_match(self):
        exact_match = make_exact_match_evaluator()
        assert exact_match("", {"expected_output": [""]}) is True

    def test_only_first_expected_item_is_compared(self):
        """When expected contains multiple items, only the first is the ground truth."""
        exact_match = make_exact_match_evaluator()
        assert exact_match("b", {"expected_output": ["a", "b"]}) is False


class TestMakeContainsEvaluator:
    def test_returns_callable_named_contains(self):
        fn = make_contains_evaluator()
        assert callable(fn)
        assert fn.__name__ == "contains"  # ty: ignore[unresolved-attribute]

    def test_substring_present_returns_true(self):
        contains = make_contains_evaluator()
        assert contains("The answer is 42", {"expected_output": ["42"]}) is True

    def test_full_string_match_returns_true(self):
        contains = make_contains_evaluator()
        assert contains("exact", {"expected_output": ["exact"]}) is True

    def test_bare_string_expected(self):
        contains = make_contains_evaluator()
        assert contains("needle in a haystack", {"expected_output": "needle"}) is True

    def test_substring_absent_returns_false(self):
        contains = make_contains_evaluator()
        assert contains("The answer is 42", {"expected_output": ["43"]}) is False

    def test_case_sensitive(self):
        contains = make_contains_evaluator()
        assert contains("Hello World", {"expected_output": ["hello"]}) is False

    def test_none_output_returns_false(self):
        contains = make_contains_evaluator()
        assert contains(None, {"expected_output": ["hello"]}) is False  # ty: ignore[invalid-argument-type]

    def test_empty_expected_returns_false(self):
        contains = make_contains_evaluator()
        assert contains("hello", {"expected_output": []}) is False

    def test_missing_key_returns_false(self):
        contains = make_contains_evaluator()
        assert contains("hello", {}) is False

    def test_empty_output_with_nonempty_needle_returns_false(self):
        contains = make_contains_evaluator()
        assert contains("", {"expected_output": ["needle"]}) is False

    def test_empty_needle_in_any_output_returns_true(self):
        """An empty substring is always contained in any string."""
        contains = make_contains_evaluator()
        assert contains("anything", {"expected_output": [""]}) is True

    def test_inversion_pattern(self):
        """Callers can negate to check output is not present."""
        contains = make_contains_evaluator()
        assert contains("safe text", {"expected_output": ["forbidden"]}) is not True


class TestMakeRegexEvaluator:
    def test_returns_callable_named_regex_match(self):
        fn = make_regex_evaluator()
        assert callable(fn)
        assert fn.__name__ == "regex_match"  # ty: ignore[unresolved-attribute]

    def test_digit_pattern_matches(self):
        regex_match = make_regex_evaluator()
        assert regex_match("order-1234", {"expected_output": [r"\d{4}"]}) is True

    def test_partial_match_via_re_search(self):
        """re.search matches anywhere in the string, not just at the start."""
        regex_match = make_regex_evaluator()
        assert regex_match("abc123def", {"expected_output": [r"\d+"]}) is True

    def test_full_pattern_match(self):
        regex_match = make_regex_evaluator()
        assert (
            regex_match("2024-01-15", {"expected_output": [r"^\d{4}-\d{2}-\d{2}$"]})
            is True
        )

    def test_bare_string_expected(self):
        regex_match = make_regex_evaluator()
        assert regex_match("hello world", {"expected_output": r"hello"}) is True

    def test_pattern_not_matched_returns_false(self):
        regex_match = make_regex_evaluator()
        assert regex_match("no digits here", {"expected_output": [r"\d+"]}) is False

    def test_anchored_pattern_fails_on_partial(self):
        regex_match = make_regex_evaluator()
        assert (
            regex_match(
                "prefix-2024-01-15-suffix",
                {"expected_output": [r"^\d{4}-\d{2}-\d{2}$"]},
            )
            is False
        )

    def test_none_output_returns_false(self):
        regex_match = make_regex_evaluator()
        assert regex_match(None, {"expected_output": [r"\d+"]}) is False  # ty: ignore[invalid-argument-type]

    def test_empty_pattern_returns_false(self):
        regex_match = make_regex_evaluator()
        assert regex_match("hello", {"expected_output": [""]}) is False

    def test_missing_key_returns_false(self):
        regex_match = make_regex_evaluator()
        assert regex_match("hello", {}) is False

    def test_empty_expected_list_returns_false(self):
        regex_match = make_regex_evaluator()
        assert regex_match("hello", {"expected_output": []}) is False

    def test_invalid_regex_raises_re_error(self):
        regex_match = make_regex_evaluator()
        with pytest.raises(re.error):
            regex_match("hello", {"expected_output": ["[invalid"]})


class TestMakeJsonMatchEvaluator:
    def test_returns_callable_named_json_match(self):
        fn = make_json_match_evaluator()
        assert callable(fn)
        assert fn.__name__ == "json_match"  # ty: ignore[unresolved-attribute]

    def test_all_keys_match_returns_1(self):
        json_match = make_json_match_evaluator()
        output = json.dumps({"a": 1, "b": "hello"})
        expected_json = json.dumps({"a": 1, "b": "hello"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(1.0)

    def test_partial_keys_match_returns_partial_score(self):
        # 1 of 2 keys match → 0.5
        json_match = make_json_match_evaluator()
        output = json.dumps({"a": 1, "b": "wrong"})
        expected_json = json.dumps({"a": 1, "b": "hello"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(0.5)

    def test_no_keys_match_returns_0(self):
        json_match = make_json_match_evaluator()
        output = json.dumps({"a": 99, "b": "nope"})
        expected_json = json.dumps({"a": 1, "b": "hello"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(0.0)

    def test_keys_filter_restricts_check(self):
        json_match = make_json_match_evaluator(keys=["a"])
        # "b" differs but is excluded — only "a" is checked
        output = json.dumps({"a": 1, "b": "ignored"})
        expected_json = json.dumps({"a": 1, "b": "expected"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(1.0)

    def test_keys_filter_partial_match(self):
        json_match = make_json_match_evaluator(keys=["a", "b"])
        output = json.dumps({"a": 1, "b": "wrong", "c": "extra"})
        expected_json = json.dumps({"a": 1, "b": "right"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(0.5)

    def test_invalid_json_output_returns_0(self):
        json_match = make_json_match_evaluator()
        assert json_match(
            "not json at all", {"expected_output": ['{"a": 1}']}
        ) == pytest.approx(0.0)

    def test_non_object_json_output_returns_0(self):
        json_match = make_json_match_evaluator()
        assert json_match(
            "[1, 2, 3]", {"expected_output": ['{"a": 1}']}
        ) == pytest.approx(0.0)

    def test_missing_key_in_output_returns_0_for_that_key(self):
        # "b" is in expected but not in output → that key scores 0
        json_match = make_json_match_evaluator()
        output = json.dumps({"a": 1})
        expected_json = json.dumps({"a": 1, "b": "missing"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(0.5)

    def test_none_output_returns_0(self):
        json_match = make_json_match_evaluator()
        assert json_match(None, {"expected_output": ['{"a": 1}']}) == pytest.approx(0.0)  # ty: ignore[invalid-argument-type]

    def test_empty_expected_returns_0(self):
        json_match = make_json_match_evaluator()
        assert json_match('{"a": 1}', {"expected_output": []}) == pytest.approx(0.0)

    def test_missing_key_returns_0(self):
        json_match = make_json_match_evaluator()
        assert json_match('{"a": 1}', {}) == pytest.approx(0.0)

    def test_extra_keys_in_output_are_ignored(self):
        """Output may contain more keys than expected; only expected keys are scored."""
        json_match = make_json_match_evaluator()
        output = json.dumps({"a": 1, "b": "hello", "extra": True})
        expected_json = json.dumps({"a": 1, "b": "hello"})
        assert json_match(
            output, {"expected_output": [expected_json]}
        ) == pytest.approx(1.0)


_SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}


class TestMakeSchemaEvaluator:
    def test_returns_callable_named_schema_valid(self):
        fn = make_schema_evaluator(_SIMPLE_SCHEMA)
        assert callable(fn)
        assert fn.__name__ == "schema_valid"  # ty: ignore[unresolved-attribute]

    def test_valid_json_matching_schema_returns_true(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        output = json.dumps({"name": "Alice", "age": 30})
        assert schema_valid(output, {}) is True

    def test_extra_fields_are_allowed_by_default(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        output = json.dumps({"name": "Bob", "age": 25, "city": "Paris"})
        assert schema_valid(output, {}) is True

    def test_missing_required_field_returns_false(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        output = json.dumps({"name": "Charlie"})  # "age" missing
        assert schema_valid(output, {}) is False

    def test_wrong_type_returns_false(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        output = json.dumps({"name": "Dave", "age": "thirty"})  # age should be int
        assert schema_valid(output, {}) is False

    def test_invalid_json_string_returns_false(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        assert schema_valid("not valid json {{", {}) is False

    def test_none_output_returns_false(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        assert schema_valid(None, {}) is False  # ty: ignore[invalid-argument-type]

    def test_json_array_against_object_schema_returns_false(self):
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        assert schema_valid("[1, 2, 3]", {}) is False

    def test_expected_dict_is_ignored(self):
        """schema_valid should not care what is in the expected dict."""
        schema_valid = make_schema_evaluator(_SIMPLE_SCHEMA)
        output = json.dumps({"name": "Eve", "age": 22})
        assert schema_valid(output, {"expected_output": "irrelevant"}) is True

    def test_jsonschema_absent_raises_import_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """If jsonschema is not importable, a helpful ImportError must be raised
        at factory-creation time (not at call time)."""
        monkeypatch.setitem(sys.modules, "jsonschema", None)  # type: ignore[arg-type]
        with pytest.raises(ImportError, match="jsonschema"):
            make_schema_evaluator(_SIMPLE_SCHEMA)


class TestMakeNumericToleranceEvaluator:
    def test_returns_callable_named_numeric_close(self):
        fn = make_numeric_tolerance_evaluator()
        assert callable(fn)
        assert fn.__name__ == "numeric_close"  # ty: ignore[unresolved-attribute]

    def test_exact_match_returns_true(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close("3.14", {"expected_output": ["3.14"]}) is True

    def test_within_default_atol_returns_true(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=1e-6)
        assert numeric_close("1.0000001", {"expected_output": ["1.0"]}) is True

    def test_outside_default_atol_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=1e-6)
        assert numeric_close("1.1", {"expected_output": ["1.0"]}) is False

    def test_within_custom_atol_returns_true(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=0.5)
        assert numeric_close("10.4", {"expected_output": ["10.0"]}) is True

    def test_outside_custom_atol_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=0.5)
        assert numeric_close("10.6", {"expected_output": ["10.0"]}) is False

    def test_within_rtol_returns_true(self):
        # 1% of 100 = 1.0; 100.5 is within 1% of 100
        numeric_close = make_numeric_tolerance_evaluator(atol=0.0, rtol=0.01)
        assert numeric_close("100.5", {"expected_output": ["100.0"]}) is True

    def test_outside_rtol_returns_false(self):
        # 1% of 100 = 1.0; 102 is outside 1% of 100
        numeric_close = make_numeric_tolerance_evaluator(atol=0.0, rtol=0.01)
        assert numeric_close("102.0", {"expected_output": ["100.0"]}) is False

    def test_float_output_not_string(self):
        """output may be a float directly, not just a string."""
        numeric_close = make_numeric_tolerance_evaluator(atol=0.01)
        assert numeric_close(3.14159, {"expected_output": ["3.14"]}) is True

    def test_integer_strings(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=0)
        assert numeric_close("42", {"expected_output": ["42"]}) is True

    def test_non_numeric_output_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close("not a number", {"expected_output": ["1.0"]}) is False

    def test_non_numeric_expected_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close("1.0", {"expected_output": ["not a number"]}) is False

    def test_none_output_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close(None, {"expected_output": ["1.0"]}) is False  # ty: ignore[invalid-argument-type]

    def test_empty_expected_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close("1.0", {"expected_output": []}) is False

    def test_missing_key_returns_false(self):
        numeric_close = make_numeric_tolerance_evaluator()
        assert numeric_close("1.0", {}) is False

    def test_bare_string_expected(self):
        numeric_close = make_numeric_tolerance_evaluator(atol=0.01)
        assert numeric_close("2.718", {"expected_output": "2.72"}) is True


def _make_mock_model(return_value: object) -> MagicMock:
    """Build a MagicMock that satisfies BaseChatModel.with_structured_output."""
    chain = MagicMock()
    chain.invoke.return_value = return_value
    model = MagicMock()
    model.with_structured_output.return_value = chain
    return model


class _FloatVerdict:
    """Minimal stand-in for a Pydantic BaseModel with a float score field."""

    class _FieldInfo:
        annotation = float

    model_fields = {"score": _FieldInfo()}

    def __init__(self, score: float) -> None:
        self.score = score


class _BoolVerdict:
    """Minimal stand-in for a Pydantic BaseModel with a bool score field."""

    class _FieldInfo:
        annotation = bool

    model_fields = {"score": _FieldInfo()}

    def __init__(self, score: bool) -> None:
        self.score = score


class _CustomKeyVerdict:
    """Minimal stand-in with a non-default result key."""

    class _FieldInfo:
        annotation = float

    model_fields = {"rating": _FieldInfo()}

    def __init__(self, rating: float) -> None:
        self.rating = rating


class TestMakeLlmJudgeEvaluator:
    PROMPT = "Output: {output}\nExpected: {expected_output}\nIs it correct?"

    def test_returns_callable_named_llm_judge(self):
        model = _make_mock_model(_FloatVerdict(1.0))
        fn = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        assert callable(fn)
        assert fn.__name__ == "llm_judge"  # ty: ignore[unresolved-attribute]

    def test_float_score_returned_correctly(self):
        model = _make_mock_model(_FloatVerdict(0.8))
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        result = llm_judge("Paris", {"expected_output": ["Paris"]})
        assert result == pytest.approx(0.8)

    def test_bool_score_returned_correctly(self):
        model = _make_mock_model(_BoolVerdict(True))
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _BoolVerdict)  # ty: ignore[invalid-argument-type]
        result = llm_judge("Paris", {"expected_output": ["Paris"]})
        assert result is True

    def test_custom_result_key(self):
        model = _make_mock_model(_CustomKeyVerdict(4.5))
        llm_judge = make_llm_judge_evaluator(
            model,
            self.PROMPT,
            _CustomKeyVerdict,  # ty: ignore[invalid-argument-type]
            result_key="rating",
        )
        result = llm_judge("answer", {"expected_output": ["answer"]})
        assert result == pytest.approx(4.5)

    def test_prompt_is_formatted_correctly(self):
        """Verify the chain is invoked with the formatted prompt string."""
        verdict = _FloatVerdict(1.0)
        model = _make_mock_model(verdict)
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        llm_judge("my output", {"expected_output": ["ground truth"]})
        chain = model.with_structured_output.return_value
        chain.invoke.assert_called_once_with(
            "Output: my output\nExpected: ground truth\nIs it correct?"
        )

    def test_none_output_sends_empty_string(self):
        """None output is coerced to an empty string before formatting."""
        model = _make_mock_model(_FloatVerdict(0.0))
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        llm_judge(None, {"expected_output": ["ref"]})  # ty: ignore[invalid-argument-type]
        chain = model.with_structured_output.return_value
        prompt_used = chain.invoke.call_args[0][0]
        assert "Output: \n" in prompt_used

    def test_missing_expected_key_sends_empty_string(self):
        model = _make_mock_model(_FloatVerdict(0.5))
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        llm_judge("output", {})
        chain = model.with_structured_output.return_value
        prompt_used = chain.invoke.call_args[0][0]
        assert "Expected: \n" in prompt_used

    def test_on_error_silent_float_returns_zero(self):
        model = _make_mock_model(_FloatVerdict(1.0))
        chain = model.with_structured_output.return_value
        chain.invoke.side_effect = RuntimeError("network error")
        llm_judge = make_llm_judge_evaluator(
            model,
            self.PROMPT,
            _FloatVerdict,  # ty: ignore[invalid-argument-type]
            on_error="silent",
        )
        result = llm_judge("output", {"expected_output": ["ref"]})
        assert result == pytest.approx(0.0)

    def test_on_error_silent_bool_returns_false(self):
        model = _make_mock_model(_BoolVerdict(True))
        chain = model.with_structured_output.return_value
        chain.invoke.side_effect = RuntimeError("network error")
        llm_judge = make_llm_judge_evaluator(
            model,
            self.PROMPT,
            _BoolVerdict,  # ty: ignore[invalid-argument-type]
            on_error="silent",
        )
        result = llm_judge("output", {"expected_output": ["ref"]})
        assert result is False

    def test_on_error_reraise_calls_callback_and_reraises(self):
        model = _make_mock_model(_FloatVerdict(1.0))
        chain = model.with_structured_output.return_value
        exc = RuntimeError("llm failure")
        chain.invoke.side_effect = exc

        received: list[Exception] = []
        callback = received.append

        llm_judge = make_llm_judge_evaluator(
            model,
            self.PROMPT,
            _FloatVerdict,  # ty: ignore[invalid-argument-type]
            on_error="reraise",
            error_callback=callback,
        )
        with pytest.raises(RuntimeError, match="llm failure"):
            llm_judge("output", {"expected_output": ["ref"]})

        assert len(received) == 1
        assert received[0] is exc

    def test_on_error_reraise_without_callback_raises_value_error_at_factory(self):
        model = _make_mock_model(_FloatVerdict(1.0))
        with pytest.raises(ValueError, match="error_callback"):
            make_llm_judge_evaluator(
                model,
                self.PROMPT,
                _FloatVerdict,  # ty: ignore[invalid-argument-type]
                on_error="reraise",
            )

    def test_with_structured_output_called_once_at_factory_creation(self):
        """The chain must be bound once at factory creation, not per call."""
        model = _make_mock_model(_FloatVerdict(0.5))
        llm_judge = make_llm_judge_evaluator(model, self.PROMPT, _FloatVerdict)  # ty: ignore[invalid-argument-type]
        llm_judge("a", {"expected_output": ["a"]})
        llm_judge("b", {"expected_output": ["b"]})
        model.with_structured_output.assert_called_once()
