"""Partial JSON key-value matching evaluator."""

import json
from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_json_match_evaluator(
    keys: list[str] | None = None,
) -> Callable[[str, dict], float]:
    """Return a partial JSON key-value matching evaluator.

    Parses ``output`` as a JSON object and compares specific key-value pairs
    against an expected JSON object stored in ``expected["expected_output"]``.
    Useful for evaluating tool-call outputs, structured generation, and API
    response validation.

    Parameters
    ----------
    keys:
        An optional list of key names to check.  When provided, only those
        keys are compared; keys present in the expected object but absent from
        this list are ignored.  When ``None`` (default), all keys present in
        the expected object are checked.

    Returns
    -------
    Callable[[str, dict], float]
        Evaluator with signature ``json_match(output, expected) -> float``.
        ``output`` is a JSON string representing an object.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        JSON string (or a Python-literal string) that represents the
        ground-truth object.
        Score is the fraction of checked keys whose values match exactly:
        ``n_matching / n_checked``.
        Returns ``0.0`` when ``output`` is not valid JSON, when the
        expected value is empty or not a JSON object, or when no keys are
        checked.
    """

    def json_match(output: str, expected: dict) -> float:
        if output is None:
            return 0.0

        try:
            output_obj = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return 0.0

        if not isinstance(output_obj, dict):
            return 0.0

        expected_items = _parse_expected(expected)
        if not expected_items:
            return 0.0
        try:
            expected_obj = json.loads(expected_items[0])
        except (json.JSONDecodeError, TypeError):
            return 0.0

        if not isinstance(expected_obj, dict):
            return 0.0

        keys_to_check = keys if keys is not None else list(expected_obj.keys())
        if not keys_to_check:
            return 0.0

        matching = sum(
            1
            for k in keys_to_check
            if k in expected_obj and output_obj.get(k) == expected_obj[k]
        )
        return matching / len(keys_to_check)

    json_match.__name__ = "json_match"
    return json_match
