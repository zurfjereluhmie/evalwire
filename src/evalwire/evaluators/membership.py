"""Exact-membership (label classification) evaluator."""

from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_membership_evaluator() -> Callable[[str, dict], bool]:
    """Return an exact-membership check evaluator.

    Designed for classification/routing outputs where the expected value is one
    of a small set of labels.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``is_in(output, expected) -> bool``.
        ``output`` is the predicted label string.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        ``list[str]`` or a ``str`` parseable by ``ast.literal_eval``.
        Returns ``True`` if ``output`` is in the expected list.
    """

    def is_in(output: str, expected: dict) -> bool:
        expected_items = _parse_expected(expected)
        return output in expected_items

    is_in.__name__ = "is_in"
    return is_in
