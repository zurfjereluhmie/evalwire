"""Tests for evalwire.evaluators."""

import pytest

from evalwire.evaluators import make_membership_evaluator, make_top_k_evaluator

# ---------------------------------------------------------------------------
# make_top_k_evaluator
# ---------------------------------------------------------------------------


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
        # expected_output provided as a repr'd list string
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


# ---------------------------------------------------------------------------
# make_membership_evaluator
# ---------------------------------------------------------------------------


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
