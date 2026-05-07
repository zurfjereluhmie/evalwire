"""Tests for evalwire.evaluators.composition factories."""

import pytest

from evalwire.evaluators.composition import (
    make_all_pass_evaluator,
    make_any_pass_evaluator,
    make_weighted_evaluator,
)


def _always(value):
    def evaluator(output, expected):
        return value

    return evaluator


TRUE_EVAL = _always(True)
FALSE_EVAL = _always(False)
ONE_EVAL = _always(1.0)
ZERO_EVAL = _always(0.0)
HALF_EVAL = _always(0.5)

EXPECTED = {"expected_output": ["x"]}


class TestMakeWeightedEvaluator:
    def test_function_name(self):
        fn = make_weighted_evaluator([(ONE_EVAL, 1.0)])
        assert fn.__name__ == "weighted"  # ty: ignore[unresolved-attribute]

    def test_single_evaluator_returns_its_score(self):
        fn = make_weighted_evaluator([(ONE_EVAL, 1.0)])
        assert fn("out", EXPECTED) == pytest.approx(1.0)

    def test_weights_are_normalised(self):
        fn = make_weighted_evaluator([(ONE_EVAL, 2.0), (ZERO_EVAL, 2.0)])
        assert fn("out", EXPECTED) == pytest.approx(0.5)

    def test_equal_weights_averages_scores(self):
        fn = make_weighted_evaluator([(ONE_EVAL, 1.0), (ZERO_EVAL, 1.0)])
        assert fn("out", EXPECTED) == pytest.approx(0.5)

    def test_bool_scores_treated_as_float(self):
        fn = make_weighted_evaluator([(TRUE_EVAL, 1.0), (FALSE_EVAL, 1.0)])
        assert fn("out", EXPECTED) == pytest.approx(0.5)

    def test_unequal_weights_produce_correct_result(self):
        fn = make_weighted_evaluator([(ONE_EVAL, 0.7), (ZERO_EVAL, 0.3)])
        assert fn("out", EXPECTED) == pytest.approx(0.7)

    def test_return_type_is_float(self):
        fn = make_weighted_evaluator([(TRUE_EVAL, 1.0)])
        result = fn("out", EXPECTED)
        assert isinstance(result, float)

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="at least one"):
            make_weighted_evaluator([])

    def test_negative_weight_raises_value_error(self):
        with pytest.raises(ValueError, match="non-negative"):
            make_weighted_evaluator([(ONE_EVAL, -1.0)])

    def test_all_zero_weights_raises_value_error(self):
        with pytest.raises(ValueError, match="non-zero"):
            make_weighted_evaluator([(ONE_EVAL, 0.0), (ZERO_EVAL, 0.0)])

    def test_passes_output_and_expected_to_sub_evaluators(self):
        received = []

        def recording_eval(output, expected):
            received.append((output, expected))
            return 1.0

        fn = make_weighted_evaluator([(recording_eval, 1.0)])
        fn("hello", EXPECTED)
        assert received == [("hello", EXPECTED)]


class TestMakeAllPassEvaluator:
    def test_function_name(self):
        fn = make_all_pass_evaluator([TRUE_EVAL])
        assert fn.__name__ == "all_pass"  # ty: ignore[unresolved-attribute]

    def test_all_true_returns_true(self):
        fn = make_all_pass_evaluator([TRUE_EVAL, TRUE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_one_false_returns_false(self):
        fn = make_all_pass_evaluator([TRUE_EVAL, FALSE_EVAL])
        assert fn("out", EXPECTED) is False

    def test_all_false_returns_false(self):
        fn = make_all_pass_evaluator([FALSE_EVAL, FALSE_EVAL])
        assert fn("out", EXPECTED) is False

    def test_single_true_evaluator(self):
        fn = make_all_pass_evaluator([TRUE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_single_false_evaluator(self):
        fn = make_all_pass_evaluator([FALSE_EVAL])
        assert fn("out", EXPECTED) is False

    def test_truthy_float_counts_as_pass(self):
        fn = make_all_pass_evaluator([ONE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_zero_float_counts_as_fail(self):
        fn = make_all_pass_evaluator([ZERO_EVAL])
        assert fn("out", EXPECTED) is False

    def test_return_type_is_bool(self):
        fn = make_all_pass_evaluator([TRUE_EVAL])
        assert isinstance(fn("out", EXPECTED), bool)

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="at least one"):
            make_all_pass_evaluator([])

    def test_short_circuits_on_first_failure(self):
        called = []

        def recording_eval(output, expected):
            called.append(1)
            return True

        fn = make_all_pass_evaluator([FALSE_EVAL, recording_eval])
        fn("out", EXPECTED)
        assert called == []


class TestMakeAnyPassEvaluator:
    def test_function_name(self):
        fn = make_any_pass_evaluator([TRUE_EVAL])
        assert fn.__name__ == "any_pass"  # ty: ignore[unresolved-attribute]

    def test_all_true_returns_true(self):
        fn = make_any_pass_evaluator([TRUE_EVAL, TRUE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_one_true_returns_true(self):
        fn = make_any_pass_evaluator([FALSE_EVAL, TRUE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_all_false_returns_false(self):
        fn = make_any_pass_evaluator([FALSE_EVAL, FALSE_EVAL])
        assert fn("out", EXPECTED) is False

    def test_single_true_evaluator(self):
        fn = make_any_pass_evaluator([TRUE_EVAL])
        assert fn("out", EXPECTED) is True

    def test_single_false_evaluator(self):
        fn = make_any_pass_evaluator([FALSE_EVAL])
        assert fn("out", EXPECTED) is False

    def test_truthy_float_counts_as_pass(self):
        fn = make_any_pass_evaluator([HALF_EVAL])
        assert fn("out", EXPECTED) is True

    def test_zero_float_counts_as_fail(self):
        fn = make_any_pass_evaluator([ZERO_EVAL])
        assert fn("out", EXPECTED) is False

    def test_return_type_is_bool(self):
        fn = make_any_pass_evaluator([FALSE_EVAL])
        assert isinstance(fn("out", EXPECTED), bool)

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="at least one"):
            make_any_pass_evaluator([])

    def test_short_circuits_on_first_success(self):
        called = []

        def recording_eval(output, expected):
            called.append(1)
            return False

        fn = make_any_pass_evaluator([TRUE_EVAL, recording_eval])
        fn("out", EXPECTED)
        assert called == []
